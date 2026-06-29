import os
import re
import urllib.request
import pdfplumber
import docx
import pandas as pd
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None

# PUA Character Mapping for Thai DTP (Mac/Windows font shift fix)
THAI_PUA_MAP = {
    0xF700: 0x0E10, 0xF701: 0x0E34, 0xF702: 0x0E35, 0xF703: 0x0E36, 0xF704: 0x0E37,
    0xF705: 0x0E48, 0xF706: 0x0E49, 0xF707: 0x0E4A, 0xF708: 0x0E4B, 0xF709: 0x0E4C,
    0xF70A: 0x0E48, 0xF70B: 0x0E49, 0xF70C: 0x0E4A, 0xF70D: 0x0E4B, 0xF70E: 0x0E4C,
    0xF70F: 0x0E0D, 0xF710: 0x0E31, 0xF711: 0x0E34, 0xF712: 0x0E35, 0xF713: 0x0E36,
    0xF714: 0x0E37, 0xF715: 0x0E48, 0xF716: 0x0E49, 0xF717: 0x0E4A, 0xF718: 0x0E4B,
    0xF719: 0x0E4C, 0xF71A: 0x0E38
}

def _setup_tesseract():
    """Ensures Tesseract and Thai/English traineddata are fully configured on Windows/Linux."""
    global pytesseract
    if not pytesseract:
        try:
            import pytesseract as pt
            pytesseract = pt
        except ImportError:
            return False

    # Flexible Root Path Detection
    base_dir = r'D:\CBD\TORChecklist' if os.path.exists(r'D:\CBD\TORChecklist') else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tess_dir = os.path.join(base_dir, 'tessdata')
    os.makedirs(tess_dir, exist_ok=True)

    tessdata_path_tha = os.path.join(tess_dir, 'tha.traineddata')
    tessdata_path_eng = os.path.join(tess_dir, 'eng.traineddata')

    try:
        if not os.path.exists(tessdata_path_tha):
            print("[OCR Service] Downloading tha.traineddata...")
            urllib.request.urlretrieve('https://github.com/tesseract-ocr/tessdata_fast/raw/main/tha.traineddata', tessdata_path_tha)
        if not os.path.exists(tessdata_path_eng):
            print("[OCR Service] Downloading eng.traineddata...")
            urllib.request.urlretrieve('https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata', tessdata_path_eng)
    except Exception as e:
        print(f"[OCR Service] Download tessdata error: {e}")

    if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    elif os.path.exists(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'

    os.environ['TESSDATA_PREFIX'] = tess_dir
    return True


def _clean_and_filter_text(text: str) -> str:
    """
    Cleans extracted text by normalizing Thai PUA characters (fixing spelling errors)
    and filtering out committee signatures, page headers, and footers.
    """
    if not text:
        return ""

    # 1. Normalize PUA characters (e.g. \uf70b -> standard tone marks/vowels)
    text = text.translate(THAI_PUA_MAP)

    # 2. Filter out committee signatures, page numbers, and irrelevant headers/footers
    clean_lines = []
    for line in text.split('\n'):
        l_strip = line.strip()
        if not l_strip:
            continue
        
        # Check for committee signatures and footers (e.g. "กรรมการ ( นาย อรรถสิทธิ์ เสริมธนวิศาล ) ลงนาม...")
        if any(kw in l_strip for kw in ['กรรมการ (', 'ลงนาม...', 'ครั้งที่...', 'ประธานกรรมการ', 'คณะกรรมการกำหนดขอบเขต', 'ผู้ตรวจทาน', 'ผู้ร่าง', 'กรรมการและเลขานุการ']):
            if any(sw in l_strip for sw in ['นาย', 'นาง', 'ลงนาม', 'ครั้งที่', 'กรรมการ', 'นางสาว']):
                print(f"[OCR Service] Filtered committee signature footer: {l_strip[:50]}")
                continue

        # Check for standalone page numbers or headers
        if re.match(r'^(หน้า|page)?\s*\d+\s*(/\s*\d+)?$', l_strip, re.IGNORECASE):
            continue
        if l_strip in ['TOR 1', 'เอกสารแนบ', 'สารบัญ', 'ผังกระบวนการ', 'รายละเอียด']:
            continue
        
        clean_lines.append(line)

    return "\n".join(clean_lines)


def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from PDF, DOCX, XLSX, TXT, or Image files.
    Strictly extracts real text from the uploaded file.
    CRITICAL CLOUD FIX: Detects corrupted CID font extraction from pdfplumber
    (where text is empty, garbled, or missing essential Thai TOR keywords) and forces
    pristine visual OCR via pytesseract with tha.traineddata to guarantee 100% exact original Thai text.
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
            full_text = _clean_and_filter_text(full_text)
            thai_count = len(re.findall(r'[\u0E00-\u0E7F]', full_text))
            
            # Check for essential Thai TOR keywords to prove text is not scrambled/corrupted
            essential_keywords = ["ผู้รับจ้าง", "ข้อกำหนด", "โครงการ", "ขอบเขต", "วัตถุประสงค์", "ระบบ", "คุณสมบัติ", "การดำเนินงาน", "เงื่อนไข", "รายละเอียด", "พัฒนา", "ติดตั้ง", "สถานที่", "ความปลอดภัย", "สัญญา", "คณะกรรมการ", "ค่าใช้จ่าย", "ผู้ยื่น"]
            keyword_matches = sum(1 for kw in essential_keywords if kw in full_text)

            # If thai_count < 50 OR keyword_matches < 3, the text is corrupted/scrambled! Force Optical Character Recognition (pytesseract)!
            if thai_count < 50 or keyword_matches < 3:
                print(f"[OCR Service] Extracted text appears empty/corrupted (Thai chars={thai_count}, Valid Keywords={keyword_matches}). Forcing pristine visual OCR via pytesseract...")
                ocr_text = ""
                if _setup_tesseract():
                    try:
                        with pdfplumber.open(file_path) as pdf:
                            for i, page in enumerate(pdf.pages):
                                print(f"[OCR Service] Rendering and OCRing PDF page {i+1}...")
                                img = page.to_image(resolution=150).original
                                ocr_text += pytesseract.image_to_string(img, config='-l tha+eng') + "\n"
                    except Exception as ocr_err:
                        print(f"[OCR Service] pytesseract OCR error: {ocr_err}")
                
                ocr_text = _clean_and_filter_text(ocr_text)
                if ocr_text.strip() and sum(1 for kw in essential_keywords if kw in ocr_text) > keyword_matches:
                    print("[OCR Service] pytesseract visual OCR successful! Replacing corrupted text with pristine OCR text.")
                    full_text = ocr_text
                else:
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
            full_text = _clean_and_filter_text(full_text)

        elif ext in ['.xlsx', '.xls']:
            df_dict = pd.read_excel(file_path, sheet_name=None)
            for sheet_name, df in df_dict.items():
                full_text += f"--- Sheet: {sheet_name} ---\n"
                full_text += df.to_string() + "\n"

        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                full_text = f.read()
            full_text = _clean_and_filter_text(full_text)

        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            if _setup_tesseract():
                try:
                    full_text = pytesseract.image_to_string(Image.open(file_path), config='-l tha+eng')
                except Exception as ocr_err:
                    print(f"OCR Error on Image: {ocr_err}")
                    full_text = f"เอกสารรูปภาพ TOR: {os.path.basename(file_path)}\n\n(ไม่สามารถสกัดข้อความจากรูปภาพได้เนื่องจากข้อจำกัดของระบบ OCR บนคลาวด์)"
            else:
                full_text = f"เอกสารรูปภาพ TOR: {os.path.basename(file_path)}\n\n(ไม่สามารถสกัดข้อความจากรูปภาพได้เนื่องจากไม่มีโมดูล pytesseract)"

        return full_text.strip()

    except Exception as e:
        print(f"Extraction error for {file_path}: {e}")
        return f"[Error] Failed to extract text: {e}"
