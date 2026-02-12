"""
ไฟล์ทดสอบการเชื่อมต่อ Google Sheets (ใช้ในเครื่อง Local)

วิธีใช้:
1. สร้างไฟล์ .env ในโฟลเดอร์เดียวกัน
2. ใส่ค่า GOOGLE_CREDENTIALS_JSON และ GOOGLE_SHEET_ID
3. รัน: python test_sheets.py
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from dotenv import load_dotenv

# โหลด environment variables
load_dotenv()

def test_connection():
    """ทดสอบการเชื่อมต่อ Google Sheets"""
    
    try:
        print("🔄 กำลังเชื่อมต่อ Google Sheets...")
        
        # ตั้งค่า scope
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # อ่านข้อมูล credentials
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if not creds_json:
            print("❌ ไม่พบ GOOGLE_CREDENTIALS_JSON ใน environment variables")
            return
        
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # เปิด Sheet
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        if not sheet_id:
            print("❌ ไม่พบ GOOGLE_SHEET_ID ใน environment variables")
            return
        
        sheet = client.open_by_key(sheet_id).sheet1
        
        print("✅ เชื่อมต่อสำเร็จ!")
        
        # แสดงข้อมูล
        print("\n📊 ข้อมูลใน Sheet:")
        records = sheet.get_all_records()
        print(f"   จำนวนแถวทั้งหมด: {len(records)}")
        
        if records:
            print(f"\n   ชื่อคอลัมน์: {list(records[0].keys())}")
            print(f"\n   ตัวอย่าง 5 แถวแรก:")
            for i, record in enumerate(records[:5], 1):
                print(f"   {i}. {record}")
            
            # นับชุมสาย
            chumsai_set = set()
            for record in records:
                chumsa = record.get('chumsa', '')
                if chumsa:
                    chumsai_set.add(chumsa)
            
            print(f"\n   จำนวนชุมสายทั้งหมด: {len(chumsai_set)}")
            print(f"   ชุมสายที่พบ (10 ตัวแรก): {list(sorted(chumsai_set))[:10]}")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    test_connection()
