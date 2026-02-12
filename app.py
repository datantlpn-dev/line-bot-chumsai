from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, LocationMessage, TextMessage,
    FlexSendMessage
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import math
import os
import json

app = Flask(__name__)

# ตั้งค่า LINE Bot
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

# ตั้งค่าคงที่
SEARCH_RADIUS_KM = 5  # รัศมีการค้นหา 5 กม.
MAX_RESULTS = 5  # แสดงสูงสุด 5 ชุมสาย
GOOGLE_MY_MAPS_URL = "https://www.google.com/maps/@18.521605,98.958027,13.55z/data=!4m2!6m1!1s1hyMB4Sb3fpkfYkYIFFnG6Y6-Jq3EPAQ?entry=ttu&g_ep=EgoyMDI2MDIwNC4wIKXMDSoASAFQAw%3D%3D"

# ตั้งค่า Google Sheets
def get_google_sheet():
    """เชื่อมต่อกับ Google Sheets"""
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # อ่านข้อมูล Service Account จาก Environment Variable
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        creds_dict = json.loads(creds_json)
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # เปิด Google Sheet
        sheet = client.open_by_key(os.environ.get('GOOGLE_SHEET_ID'))
        return sheet.sheet1
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        return None

def haversine_distance(lat1, lon1, lat2, lon2):
    """คำนวณระยะทางระหว่างพิกัด 2 จุด (หน่วย: กิโลเมตร)"""
    R = 6371  # รัศมีโลก (km)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def find_nearby_chumsai(user_lat, user_lng):
    """
    หาชุมสายทั้งหมดที่อยู่ในรัศมี SEARCH_RADIUS_KM
    คืนค่า: list ของ dict [{name, count, min_distance}, ...]
    """
    sheet = get_google_sheet()
    if not sheet:
        return []
    
    # อ่านข้อมูลจาก Sheet (คอลัมน์: chumsa, lat, lng)
    records = sheet.get_all_records()
    
    # สร้าง dict เก็บข้อมูลแต่ละชุมสาย
    chumsai_data = {}
    
    for record in records:
        try:
            chumsa_name = record.get('chumsa', '')
            if not chumsa_name:
                continue
                
            point_lat = float(record.get('lat', 0))
            point_lng = float(record.get('lng', 0))
            
            # คำนวณระยะทาง
            distance = haversine_distance(user_lat, user_lng, point_lat, point_lng)
            
            # เก็บข้อมูลชุมสาย
            if chumsa_name not in chumsai_data:
                chumsai_data[chumsa_name] = {
                    'name': chumsa_name,
                    'count': 0,
                    'min_distance': float('inf')
                }
            
            # นับจำนวนจุด
            chumsai_data[chumsa_name]['count'] += 1
            
            # เก็บระยะทางที่ใกล้ที่สุด
            if distance < chumsai_data[chumsa_name]['min_distance']:
                chumsai_data[chumsa_name]['min_distance'] = distance
                
        except (ValueError, TypeError) as e:
            print(f"Error processing record: {e}")
            continue
    
    # กรองเฉพาะชุมสายที่อยู่ในรัศมี
    nearby = [
        data for data in chumsai_data.values() 
        if data['min_distance'] <= SEARCH_RADIUS_KM
    ]
    
    # เรียงตามระยะทางจากน้อยไปมาก
    nearby.sort(key=lambda x: x['min_distance'])
    
    # จำกัดจำนวนสูงสุด
    return nearby[:MAX_RESULTS]

def create_flex_message(nearby_chumsai):
    """สร้าง Flex Message แสดงชุมสายใกล้เคียง"""
    
    if not nearby_chumsai:
        # กรณีไม่เจอชุมสายในรัศมี
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "❌ ไม่พบชุมสายใกล้เคียง",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#FF6B6B"
                    },
                    {
                        "type": "text",
                        "text": f"ไม่พบชุมสายในรัศมี {SEARCH_RADIUS_KM} กม.",
                        "size": "sm",
                        "color": "#999999",
                        "margin": "md",
                        "wrap": True
                    },
                    {
                        "type": "separator",
                        "margin": "lg"
                    },
                    {
                        "type": "text",
                        "text": "คุณสามารถเปิดแผนที่ทั้งหมดเพื่อดูตำแหน่งชุมสายทั้งหมดได้",
                        "size": "xs",
                        "color": "#666666",
                        "margin": "md",
                        "wrap": True
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "action": {
                            "type": "uri",
                            "label": "🗺️ เปิดแผนที่ทั้งหมด",
                            "uri": GOOGLE_MY_MAPS_URL
                        },
                        "color": "#1DB954"
                    }
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text="ไม่พบชุมสายใกล้เคียง",
            contents=flex_content
        )
    
    # สร้าง header
    header = {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "📍 ชุมสายใกล้เคียงคุณ",
                "weight": "bold",
                "size": "xl",
                "color": "#ffffff"
            },
            {
                "type": "text",
                "text": f"ภายในรัศมี {SEARCH_RADIUS_KM} กม.",
                "size": "xs",
                "color": "#ffffff",
                "margin": "xs"
            }
        ],
        "backgroundColor": "#1DB954",
        "paddingAll": "20px"
    }
    
    # สร้าง body (รายการชุมสาย)
    body_contents = []
    
    medal_icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    
    for idx, chumsa in enumerate(nearby_chumsai):
        medal = medal_icons[idx] if idx < len(medal_icons) else "📍"
        
        # ชื่อชุมสาย
        chumsa_box = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"{medal} {chumsa['name']}",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#1DB954",
                    "wrap": True
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "margin": "sm",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📏",
                            "size": "sm",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": f"ระยะทาง: {chumsa['min_distance']:.2f} กม.",
                            "size": "sm",
                            "color": "#666666",
                            "margin": "sm",
                            "flex": 1
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "margin": "xs",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📌",
                            "size": "sm",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": f"จำนวน: {chumsa['count']} จุด",
                            "size": "sm",
                            "color": "#666666",
                            "margin": "sm",
                            "flex": 1
                        }
                    ]
                },
                {
                    "type": "button",
                    "style": "primary",
                    "height": "sm",
                    "margin": "md",
                    "action": {
                        "type": "uri",
                        "label": "🗺️ เปิดแผนที่",
                        "uri": GOOGLE_MY_MAPS_URL
                    },
                    "color": "#1DB954"
                }
            ],
            "margin": "lg" if idx > 0 else "none",
            "paddingAll": "10px",
            "backgroundColor": "#F8F8F8",
            "cornerRadius": "10px"
        }
        
        body_contents.append(chumsa_box)
    
    body = {
        "type": "box",
        "layout": "vertical",
        "contents": body_contents,
        "paddingAll": "15px"
    }
    
    # รวมเป็น bubble
    flex_content = {
        "type": "bubble",
        "size": "mega",
        "header": header,
        "body": body
    }
    
    return FlexSendMessage(
        alt_text=f"พบ {len(nearby_chumsai)} ชุมสายใกล้เคียง",
        contents=flex_content
    )

@app.route("/")
def home():
    """หน้าแรกเพื่อเช็คว่า Bot ทำงาน"""
    return "LINE Bot Chumsai Finder is running! ✅"

@app.route("/api/webhook", methods=['POST'])
def callback():
    """Webhook สำหรับรับข้อความจาก LINE"""
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    """จัดการเมื่อผู้ใช้ส่งพิกัดมา"""
    user_lat = event.message.latitude
    user_lng = event.message.longitude
    
    # หาชุมสายใกล้เคียง
    nearby = find_nearby_chumsai(user_lat, user_lng)
    
    # ส่ง Flex Message กลับไป
    flex_msg = create_flex_message(nearby)
    line_bot_api.reply_message(event.reply_token, flex_msg)

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    """จัดการข้อความทั่วไป"""
    text = event.message.text
    
    if text.lower() in ['สวัสดี', 'hello', 'hi', 'หวัดดี']:
        reply = "สวัสดีครับ! 👋\n\n📍 กรุณาส่งพิกัด (Location) มาให้บอท\n\nบอทจะค้นหาชุมสายใกล้เคียงภายในรัศมี 5 กม. ให้คุณครับ"
    elif 'ช่วย' in text or 'help' in text.lower():
        reply = f"📖 วิธีใช้งาน:\n\n1. กดปุ่ม '+' ใน LINE\n2. เลือก 'ตำแหน่งที่อยู่'\n3. เลือกตำแหน่งปัจจุบัน หรือค้นหาสถานที่\n4. ส่งตำแหน่งมาให้บอท\n\nบอทจะแสดงชุมสายใกล้เคียง (รัศมี {SEARCH_RADIUS_KM} กม.) ให้คุณเลือกดูได้เลยครับ!"
    else:
        reply = "❓ กรุณาส่งพิกัด (Location) เพื่อค้นหาชุมสายใกล้เคียง\n\nหรือพิมพ์ 'ช่วย' เพื่อดูวิธีใช้งาน"
    
    line_bot_api.reply_message(
        event.reply_token,
        TextMessage(text=reply)
    )

# สำหรับ Vercel
if __name__ == "__main__":
    app.run()
