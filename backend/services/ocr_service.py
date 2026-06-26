import os
import pdfplumber
import docx
import pandas as pd
import pytesseract
from PIL import Image

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from PDF, DOCX, XLSX, TXT, or Image files.
    Strictly extracts real text from the uploaded file without any hardcoded mock fallbacks.
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
            
            # If pdfplumber and tesseract failed (e.g. scanned PDF on cloud without tesseract binary), salvage raw text strings from binary
            if not full_text.strip():
                print("Extracting raw readable strings directly from PDF binary structure...")
                with open(file_path, 'rb') as f:
                    raw_content = f.read().decode('utf-8', errors='ignore')
                    # Keep Thai, English characters and numbers
                    full_text = "".join([c for c in raw_content if c.isalnum() or c.isspace()])
                
                if not full_text.strip():
                    # If completely unreadable binary, return a notification indicating exact file name and status
                    full_text = f"เอกสาร TOR: {os.path.basename(file_path)}\n\nไม่พบข้อความที่สามารถสกัดได้ในไฟล์นี้ (ไฟล์อาจเป็นรูปภาพสแกนที่ไม่มีข้อความเลเยอร์ หรือเข้ารหัส)"

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
                full_text = f"เอกสารรูปภาพ TOR: {os.path.basename(file_path)}\n\n(ไม่สามารถสกัดข้อความจากรูปภาพได้เนื่องจากข้อจำกัดของระบบ OCR บนคลาวด์)"

        return full_text.strip()

    except Exception as e:
        print(f"Extraction error for {file_path}: {e}")
        return f"[Error] Failed to extract text: {e}"
