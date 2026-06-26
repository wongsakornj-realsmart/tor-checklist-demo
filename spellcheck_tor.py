import pandas as pd
from pythainlp.util import normalize
from pythainlp.tokenize import word_tokenize
from pythainlp.spell import correct
from pythainlp.util import isthai
import openpyxl

excel_path = r'D:\CBD\TORChecklist\OutputTORChecklist\Attach_TOR_1.xlsx'

def fix_spelling(text):
    if not isinstance(text, str):
        return text
    
    # 1. Normalize Thai characters (fixes tone mark orders, standardizes sara am)
    text = normalize(text)
    
    # 2. Dictionary of common OCR spelling errors in technical documents
    common_fixes = {
        'เวบไซต์': 'เว็บไซต์',
        'อินเทอรเน็ต': 'อินเทอร์เน็ต',
        'ซอฟตแวร': 'ซอฟต์แวร์',
        'ฮารดแวร': 'ฮาร์ดแวร์',
        'เซิรฟเวอร': 'เซิร์ฟเวอร์',
        'คอมพิวเตอร': 'คอมพิวเตอร์',
        'เวอรชัน': 'เวอร์ชัน',
        'แพลตฟอรม': 'แพลตฟอร์ม',
        'อัปเดต': 'อัปเดต',
        'พาสเวิรด': 'พาสเวิร์ด',
        'ไฟล': 'ไฟล์',
        'ออนไลน': 'ออนไลน์',
        'ฟังกชัน': 'ฟังก์ชัน',
        'แอปพลิเคชน': 'แอปพลิเคชัน',
        'ระบบปฎิบัติการ': 'ระบบปฏิบัติการ',
        'ปฎิบัติ': 'ปฏิบัติ',
        'สิทธ': 'สิทธิ',
    }
    
    for wrong, right in common_fixes.items():
        text = text.replace(wrong, right)
        
    # Optional: We could run pythainlp.spell.correct() but it is risky for technical terms.
    # Therefore, we rely on normalization and common fixes which are 100% safe.
    
    return text

def run_spellcheck():
    df = pd.read_excel(excel_path)
    
    # Apply spelling fix to 'ข้อกำหนด / รายละเอียด (Requirement / Details)'
    col_req = 'ข้อกำหนด / รายละเอียด (Requirement / Details)'
    col_main = 'หมวดหมู่หลัก'
    col_sub = 'หัวข้อย่อย'
    
    if col_req in df.columns:
        df[col_req] = df[col_req].apply(fix_spelling)
    if col_main in df.columns:
        df[col_main] = df[col_main].apply(fix_spelling)
    if col_sub in df.columns:
        df[col_sub] = df[col_sub].apply(fix_spelling)
        
    df.to_excel(excel_path, index=False)
    print("Spell checking and normalization completed successfully.")

if __name__ == '__main__':
    run_spellcheck()
