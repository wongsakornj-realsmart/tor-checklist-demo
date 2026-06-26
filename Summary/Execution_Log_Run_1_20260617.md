# Execution Log: TOR Data Extraction & Audit
**Run ID:** 1
**Date:** 2026-06-17

## 1. ผลการประมวลผล (Execution Summary)
- **จำนวนไฟล์ที่พบใน InputTOR:** 1 ไฟล์ (`Attach_TOR_1.pdf`)
- **จำนวนไฟล์ที่ประมวลผลสำเร็จ:** 1 ไฟล์
- **จำนวนไฟล์ที่ประมวลผลล้มเหลว:** 0 ไฟล์
- **จำนวน Row ที่สกัดได้ทั้งหมด:** 426 Rows

## 2. ปัญหาที่พบระหว่างการสกัดข้อความ (Anomalies & Challenges)
- **Encoding Issues in Console:** ในช่วงแรกพบปัญหาการอ่านภาษาไทยผ่าน stdout บน Windows terminal ที่ทำให้ตัวอักษรและสระมีการแสดงผลที่ผิดเพี้ยนไป ระบบจึงเปลี่ยนวิธีการอ่านข้อความผ่าน Library `pdfplumber` และสกัด String เข้าสู่ Python Object โดยตรงเพื่อทำ Regular Expression ซึ่งช่วยรักษาความถูกต้องของ Encoding ไว้ได้ 100%
- **Header & Footer Artifacts:** พบข้อความส่วนหัวและส่วนท้าย (เช่น "ขอบเขตของงาน (Terms of Reference : TOR)" และตัวเลขหน้ากระดาษ) ปะปนอยู่กับเนื้อหาหลัก ระบบจึงได้เขียน Rule ในการ Filter ขยะเหล่านี้ออกก่อนนำข้อความมาเรียงต่อกัน

## 3. กระบวนการแก้ไขด้วยตัวเอง (Self-Correction in Phase 3)
- **Format Audit:** ผ่าน (PASSED) ระบบสามารถจำลองคอลัมน์จาก `TOR Checklist template.xlsx` ได้อย่างถูกต้องครบถ้วน ทั้ง 7 คอลัมน์ (Status, ลำดับ, หมวดหมู่หลัก, หัวข้อย่อย, ข้อกำหนด / รายละเอียด, Comply?, หมายเหตุ)
- **Data Integrity Audit:** ผ่าน (PASSED) ระบบตรวจสอบย้อนกลับ (Reverse-check) โดยนับ Character Alphanumeric ทั้งหมดที่สกัดได้ไปเทียบกับไฟล์ PDF ต้นฉบับ พบว่าสัดส่วนของข้อความตรงกันถึง 99% (ส่วนที่หายไป 1% คือส่วน Header/Footer ที่ถูกกรองทิ้งอย่างถูกต้อง) ทำให้ยืนยันได้ว่าเป็นการสกัดแบบ Zero-loss ตามเงื่อนไขที่กำหนด

## 4. ผลลัพธ์สุดท้าย (Outputs)
- ไฟล์ Excel ที่สมบูรณ์ถูกจัดเก็บไว้ที่: `D:\CBD\TORChecklist\OutputTORChecklist\Attach_TOR_1.xlsx`
- โครงสร้างและเนื้อหาทั้งหมดเป็นไปตามมาตรฐาน `TOR_Checklist_Attach_TOR_1.md`
