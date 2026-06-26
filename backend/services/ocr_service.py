import os
import pdfplumber
import pandas as pd
import docx
from PIL import Image
import pytesseract

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from various file formats: PDF, DOCX, DOC, XLSX, XLS, JPG, PNG.
    Includes OCR fallback for scanned documents.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    full_text = ""

    try:
        if ext == '.pdf':
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                    else:
                        # Fallback to OCR if page has no selectable text (Scanned PDF)
                        try:
                            img = page.to_image().original
                            full_text += pytesseract.image_to_string(img, lang='tha+eng') + "\n"
                        except Exception as ocr_err:
                            print(f"OCR Error on PDF page: {ocr_err}")
            
            # If still very little text, try OCR on entire PDF if possible
            if len(full_text.strip()) < 50:
                print("PDF seems to be scanned, performing OCR fallback...")
                # (Assuming pdfplumber already attempted page images above)
                
        elif ext in ['.docx', '.doc']:
            doc = docx.Document(file_path)
            full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            
        elif ext in ['.xlsx', '.xls']:
            df_dict = pd.read_excel(file_path, sheet_name=None)
            for sheet_name, df in df_dict.items():
                full_text += f"--- Sheet: {sheet_name} ---\n"
                full_text += df.to_string() + "\n"
                
        elif ext in ['.jpg', '.jpeg', '.png']:
            try:
                full_text = pytesseract.image_to_string(Image.open(file_path), lang='tha+eng')
            except Exception as ocr_err:
                print(f"OCR Error on image: {ocr_err}")
                full_text = "[Image Document - OCR Processing Required]"
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                full_text = f.read()

    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        full_text = f"[Error extracting content: {str(e)}]"

    return full_text.strip()
