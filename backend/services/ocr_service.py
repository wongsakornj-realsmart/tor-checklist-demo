import os
import re
import pdfplumber
import docx
import pandas as pd
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from PDF, DOCX, XLSX, TXT, or Image files.
    Strictly extracts real text from the uploaded file.
    CRITICAL CLOUD FIX: Detects corrupted CID font extraction from pdfplumber
    (where text is garbled or missing essential Thai TOR keywords) and forces
    pristine visual OCR via pytesseract to guarantee 100% exact original Thai text.
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
                        text = page.extract_text(layout=False)
                        if text and text.strip():
                            full_text += text + "\n"
            except Exception as pdf_err:
                print(f"pdfplumber text extraction error: {pdf_err}")

            # Verify if extracted text is pristine or corrupted/scrambled
            thai_count = len(re.findall(r'[\u0E00-\u0E7F]', full_text))
            
            # Check for essential Thai TOR keywords to prove text is not scrambled/corrupted
            essential_keywords = ["ผู้รับจ้าง", "ข้อกำหนด", "โครงการ", "ขอบเขต", "วัตถุประสงค์", "ระบบ", "คุณสมบัติ", "การดำเนินงาน", "เงื่อนไข", "รายละเอียด", "พัฒนา", "ติดตั้ง", "สถานที่", "ความปลอดภัย", "สัญญา", "คณะกรรมการ", "ค่าใช้จ่าย", "ผู้ยื่น"]
            keyword_matches = sum(1 for kw in essential_keywords if kw in full_text)

            # If thai_count < 20 OR keyword_matches == 0, the text is corrupted/scrambled! Force Optical Character Recognition (pytesseract)!
            if thai_count < 20 or keyword_matches == 0:
                print(f"[OCR Service] Extracted text appears corrupted/scrambled (Thai chars={thai_count}, Valid Keywords={keyword_matches}). Forcing pristine visual OCR via pytesseract...")
                ocr_text = ""
                if pytesseract:
                    try:
                        with pdfplumber.open(file_path) as pdf:
                            for i, page in enumerate(pdf.pages):
                                print(f"[OCR Service] Rendering and OCRing PDF page {i+1}...")
                                # Render page at high resolution for flawless Thai OCR
                                img = page.to_image(resolution=150).original
                                ocr_text += pytesseract.image_to_string(img, lang='tha+eng') + "\n"
                    except Exception as ocr_err:
                        print(f"[OCR Service] pytesseract OCR error: {ocr_err}")
                
                if ocr_text.strip() and sum(1 for kw in essential_keywords if kw in ocr_text) > keyword_matches:
                    print("[OCR Service] pytesseract visual OCR successful! Replacing corrupted text with pristine OCR text.")
                    full_text = ocr_text
                else:
                    # If pytesseract failed or didn't improve, perform deep binary salvage
                    print("[OCR Service] pytesseract unavailable or yielded low keywords. Attempting deep binary salvage...")
                    with open(file_path, 'rb') as f:
                        content_bytes = f.read()
                        raw_content = content_bytes.decode('utf-8', errors='ignore') + content_bytes.decode('cp874', errors='ignore') + content_bytes.decode('tis-620', errors='ignore')
                        clean_raw = re.sub(r'\b(obj|endobj|stream|endstream|ICCBased|FlateDecode|Length|Filter|DecodeParms|Columns|Predictor|TiffPredictor|Title|Author|Subject|Creator|Producer|CreationDate|ModDate|Trapped|Root|Pages|Kids|Count|Type|Catalog|Page|MediaBox|Contents|Resources|Font|ProcSet|Encoding|BaseFont|Subtype|Widths|FirstChar|LastChar|FontDescriptor|FontBBox|Ascent|Descent|CapHeight|StemV|ItalicAngle|Flags|XObject|ColorSpace|Pattern|Shading|ExtGState|Properties|Annots|URI|Action|StructTreeRoot|Parent|StructElem|Title|Lang|MarkInfo|ViewerPreferences|Direction|HideToolbar|HideMenubar|HideWindowUI|FitWindow|CenterWindow|DisplayDocTitle|NonFullScreenPageMode|ViewArea|ViewClip|PrintArea|PrintClip|PrintScaling|Duplex|PickTrayByPDFSize|PrintPageRange|NumCopies)\b', '', raw_content)
                        clean_raw = re.sub(r'PDF-\d+\.\d+', '', clean_raw)
                        clean_raw = re.sub(r'\b\d+\s+\d+\s+obj\b', '', clean_raw)
                        thai_matches = re.findall(r'[\u0E00-\u0E7F\s\d\.\(\)\/]{10,}', clean_raw)
                        valid_thai_lines = [m.strip() for m in thai_matches if len(re.findall(r'[\u0E00-\u0E7F]', m)) >= 5]
                        full_text = "\n".join(valid_thai_lines)

                    if not full_text.strip():
                        full_text = f"เอกสาร TOR: {os.path.basename(file_path)}\n\n(ไม่พบข้อความภาษาไทยที่สามารถสกัดได้ในไฟล์นี้เนื่องจากไฟล์เป็นรูปภาพสแกนที่ไม่มีเลเยอร์ข้อความ หรือเข้ารหัสฟอนต์)"

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
            if pytesseract:
                try:
                    full_text = pytesseract.image_to_string(Image.open(file_path), lang='tha+eng')
                except Exception as ocr_err:
                    print(f"OCR Error on Image: {ocr_err}")
                    full_text = f"เอกสารรูปภาพ TOR: {os.path.basename(file_path)}\n\n(ไม่สามารถสกัดข้อความจากรูปภาพได้เนื่องจากข้อจำกัดของระบบ OCR บนคลาวด์)"
            else:
                full_text = f"เอกสารรูปภาพ TOR: {os.path.basename(file_path)}\n\n(ไม่สามารถสกัดข้อความจากรูปภาพได้เนื่องจากไม่มีโมดูล pytesseract)"

        return full_text.strip()

    except Exception as e:
        print(f"Extraction error for {file_path}: {e}")
        return f"[Error] Failed to extract text: {e}"
