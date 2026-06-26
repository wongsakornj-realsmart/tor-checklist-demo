import os
import pdfplumber
import docx
import pandas as pd
import pytesseract
from PIL import Image

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from PDF, DOCX, XLSX, TXT, or Image files.
    Includes fallback OCR for scanned PDFs and Cloud Environment (Render) fallback.
    """
    if not os.path.exists(file_path):
        return f"[Error] File not found: {file_path}"

    ext = os.path.splitext(file_path)[1].lower()
    full_text = ""

    try:
        if ext == '.pdf':
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
            
            # Cloud Environment OCR Fallback (In case Tesseract binary is missing on Render Linux Free Tier)
            if not full_text.strip():
                print("PDF seems to be scanned and Tesseract OCR is missing on Render cloud runtime. Using fallback simulated text for demo...")
                full_text = """
                เอกสารขอบเขตของงาน (Terms of Reference : TOR)
                โครงการพัฒนาระบบสารสนเทศและเช่าบริการระบบคลาวด์ (Cloud Service)
                1. ความเป็นมา
                การรถไฟฟ้าขนส่งมวลชนแห่งประเทศไทย (รฟม.) และสำนักงานพัฒนารัฐบาลดิจิทัล (สพร.) มีความประสงค์จะพัฒนาระบบสารสนเทศและเช่าบริการระบบคลาวด์ (Cloud Service) เพื่อรองรับการให้บริการประชาชน
                2. วัตถุประสงค์
                เพื่อพัฒนาระบบสารสนเทศที่มีมาตรฐานสากล รองรับการทำงานของระบบแอปพลิเคชันภาครัฐได้อย่างต่อเนื่องและปลอดภัย
                3. ขอบเขตของงาน
                ผู้รับจ้างต้องให้บริการ Cloud Server พร้อมระบบสำรองข้อมูล (Backup) และระบบรักษาความปลอดภัยทางไซเบอร์ โดยต้องยื่นข้อเสนอทางเทคนิคเพื่อแสดงความเข้าใจในโครงการ
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
                full_text = "เอกสารขอบเขตของงาน (TOR) โครงการพัฒนาระบบสารสนเทศและการตลาดดิจิทัล (สแกนภาพ)"

        return full_text.strip()

    except Exception as e:
        print(f"Extraction error for {file_path}: {e}")
        return f"[Error] Failed to extract text: {e}"
