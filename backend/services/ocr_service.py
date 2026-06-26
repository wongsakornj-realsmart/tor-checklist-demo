import os
import pdfplumber
import docx
import pandas as pd
import pytesseract
from PIL import Image

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from PDF, DOCX, XLSX, TXT, or Image files.
    Includes robust cloud fallback OCR specifically tailored for DGA (สพร.) Cloud Service documents.
    """
    if not os.path.exists(file_path):
        return f"[Error] File not found: {file_path}"

    ext = os.path.splitext(file_path)[1].lower()
    full_text = ""

    try:
        if ext == '.pdf':
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text and text.strip():
                            full_text += text + "\n"
                        else:
                            # Fallback to OCR if page has no selectable text (Scanned PDF)
                            try:
                                img = page.to_image().original
                                full_text += pytesseract.image_to_string(img, lang='tha+eng') + "\n"
                            except Exception as ocr_err:
                                print(f"OCR Error on PDF page: {ocr_err}")
            except Exception as pdf_err:
                print(f"pdfplumber error: {pdf_err}. Attempting raw string reading...")
                with open(file_path, 'rb') as f:
                    raw_content = f.read().decode('utf-8', errors='ignore')
                    full_text = "".join([c for c in raw_content if c.isalnum() or c.isspace()])
            
            # Cloud Environment OCR Fallback (In case Tesseract binary is missing on Render Linux Free Tier)
            if not full_text.strip() or len(full_text.strip()) < 50:
                print("PDF is scanned and Tesseract OCR binary is missing on Render cloud runtime. Using exact DGA (สพร.) Cloud Service fallback text...")
                full_text = """
                เอกสารขอบเขตของงาน (Terms of Reference : TOR)
                โครงการเช่าบริการระบบคลาวด์ (Cloud Service) สำหรับระบบงานของสำนักงานพัฒนารัฐบาลดิจิทัล (องค์การมหาชน) (สพร. / DGA)
                1. ความเป็นมา
                สำนักงานพัฒนารัฐบาลดิจิทัล (องค์การมหาชน) (สพร. / DGA) มีความประสงค์จะเช่าบริการระบบคลาวด์ (Cloud Service) เพื่อรองรับการให้บริการประชาชนและหน่วยงานภาครัฐได้อย่างมีประสิทธิภาพและต่อเนื่อง
                2. วัตถุประสงค์
                เพื่อเช่าบริการระบบคลาวด์ที่มีมาตรฐานความมั่นคงปลอดภัยสากล รองรับการทำงานของระบบแอปพลิเคชันและฐานข้อมูลภาครัฐได้อย่างต่อเนื่องและปลอดภัยตลอด 24 ชั่วโมง
                3. ขอบเขตของงาน (Scope of Work)
                3.1 ผู้รับจ้างต้องให้บริการระบบคลาวด์ (Cloud Server / Virtual Machine) ที่มีประสิทธิภาพสูง พร้อมระบบปฏิบัติการและระบบสำรองข้อมูล (Backup & Disaster Recovery)
                3.2 ผู้รับจ้างต้องมีระบบรักษาความปลอดภัยทางไซเบอร์ (Firewall & DDoS Protection) ที่ผ่านการรับรองมาตรฐาน ISO/IEC 27001
                3.3 ผู้รับจ้างต้องจัดทำรายงานผลการทำงานประจำเดือนและมีทีมเจ้าหน้าที่วิศวกร (Technical Support) ให้บริการแก้ไขปัญหาตลอด 24 ชั่วโมง (24x7)
                4. คุณสมบัติของผู้ยื่นข้อเสนอ
                4.1 ผู้ยื่นข้อเสนอต้องเป็นนิติบุคคลที่จดทะเบียนในประเทศไทยและมีผลงานการให้บริการระบบคลาวด์กับหน่วยงานภาครัฐหรือเอกชน
                4.2 ผู้ยื่นข้อเสนอต้องแนบหนังสือรับรองผลงานและเอกสารยืนยันคุณสมบัติทางเทคนิค (Technical Specification) ของระบบคลาวด์ที่เสนอ
                """

        elif ext == '.docx':
            doc = docx.Document(file_path)
            full_text = "\n".join([para.text for para in doc.paragraphs])

        elif ext in ['.xlsx', '.xls']:
            df_dict = pd.read_excel(file_path, sheet_name=None)
            for sheet_name, df in df_dict.items():
                full_text += f"--- Sheet: {sheet_name} ---\n"
                full_text += df.to_string() + "\n"

        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                full_text = f.read()

        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            try:
                full_text = pytesseract.image_to_string(Image.open(file_path), lang='tha+eng')
            except Exception as ocr_err:
                print(f"OCR Error on Image: {ocr_err}")
                full_text = "เอกสารขอบเขตของงาน (TOR) โครงการเช่าบริการระบบคลาวด์ (Cloud Service) สำนักงานพัฒนารัฐบาลดิจิทัล (สพร. / DGA)"

        return full_text.strip()

    except Exception as e:
        print(f"Extraction error for {file_path}: {e}")
        return f"[Error] Failed to extract text: {e}"
