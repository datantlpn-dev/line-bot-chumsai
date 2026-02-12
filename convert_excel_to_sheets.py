"""
สคริปต์แปลงไฟล์ Excel เป็นข้อมูลที่พร้อมอัปโหลดไปยัง Google Sheets

วิธีใช้:
1. วางไฟล์ Excel (.xlsx) ในโฟลเดอร์เดียวกัน
2. รัน: python convert_excel_to_sheets.py your_file.xlsx
3. ไฟล์ CSV จะถูกสร้างที่ output.csv
4. นำ CSV ไป Import ใน Google Sheets
"""

import pandas as pd
import sys

def convert_excel_to_csv(excel_file, output_file='output.csv'):
    """แปลงไฟล์ Excel เป็น CSV"""
    
    try:
        print(f"🔄 กำลังอ่านไฟล์ {excel_file}...")
        
        # อ่านไฟล์ Excel
        df = pd.read_excel(excel_file)
        
        print(f"✅ อ่านไฟล์สำเร็จ!")
        print(f"   จำนวนแถว: {len(df)}")
        print(f"   คอลัมน์: {df.columns.tolist()}")
        
        # ตรวจสอบคอลัมน์ที่จำเป็น
        required_cols = ['chumsa', 'lat', 'lng']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"⚠️ คำเตือน: ไม่พบคอลัมน์ {missing_cols}")
            print(f"   คอลัมน์ที่มี: {df.columns.tolist()}")
        else:
            print(f"✅ พบคอลัมน์ครบถ้วน: {required_cols}")
        
        # บันทึกเป็น CSV
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✅ บันทึกไฟล์ {output_file} สำเร็จ!")
        
        # แสดงตัวอย่างข้อมูล
        print(f"\nตัวอย่างข้อมูล 5 แถวแรก:")
        print(df.head())
        
        # นับชุมสาย
        if 'chumsa' in df.columns:
            chumsai_count = df['chumsa'].value_counts()
            print(f"\nจำนวนชุมสายทั้งหมด: {len(chumsai_count)}")
            print(f"\nTop 10 ชุมสายที่มีจุดมากที่สุด:")
            print(chumsai_count.head(10))
        
        print(f"\n📤 นำไฟล์ {output_file} ไป Import ใน Google Sheets:")
        print(f"   1. เปิด Google Sheets")
        print(f"   2. File > Import > Upload")
        print(f"   3. เลือกไฟล์ {output_file}")
        print(f"   4. Import location: Replace spreadsheet")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ กรุณาระบุชื่อไฟล์ Excel")
        print("   ตัวอย่าง: python convert_excel_to_sheets.py data.xlsx")
    else:
        excel_file = sys.argv[1]
        convert_excel_to_csv(excel_file)
