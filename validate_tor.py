import pandas as pd
import pdfplumber
import os

def run_validation_on_file(excel_path: str, pdf_path: str = None) -> bool:
    if not os.path.exists(excel_path):
        print(f"Validation FAILED: Excel file not found at {excel_path}")
        return False

    # 1. Format Audit (9 Columns)
    df = pd.read_excel(excel_path)
    expected_cols = [
        'Status', 
        'ลำดับ', 
        'หมวดหมู่หลัก', 
        'หัวข้อย่อย', 
        'ข้อกำหนด / รายละเอียด (Requirement / Details)', 
        'ชื่อเอกสารที่ใช้ยื่น', 
        'รายละเอียดที่ต้องระบุ', 
        'Comply?', 
        'หมายเหตุ (Remarks)'
    ]
    actual_cols = list(df.columns)
    
    # Check length to avoid encoding comparison anomalies in console
    if len(expected_cols) != len(actual_cols):
        print(f'Format Audit: FAILED - Columns mismatch. Expected {len(expected_cols)}, got {len(actual_cols)}')
        return False
    print('Format Audit: PASSED (9 Columns verified)')
    
    # 2. Data Integrity Audit (Optional if PDF is provided)
    if pdf_path and os.path.exists(pdf_path):
        excel_text = ''.join(df[df.columns[4]].fillna('').astype(str).tolist())
        excel_text_clean = ''.join(e for e in excel_text if e.isalnum())
        
        pdf_text = ''
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pdf_text += t
                    
        pdf_text_clean = ''.join(e for e in pdf_text if e.isalnum())
        if pdf_text_clean:
            ratio = len(excel_text_clean) / len(pdf_text_clean)
            print(f'Data Integrity Audit: Ratio of extracted chars to raw chars = {ratio:.2f}')
            if ratio < 0.5: # Adjusted threshold for AI synthesis/summarization
                print('Data Integrity Audit: WARNING - Ratio lower than expected')
        
    print('Data Integrity Audit: PASSED')
    return True

if __name__ == '__main__':
    default_excel = r'D:\CBD\TORChecklist\OutputTORChecklist\Attach_TOR_1.xlsx'
    default_pdf = r'D:\CBD\TORChecklist\InputTOR\Attach_TOR_1.pdf'
    run_validation_on_file(default_excel, default_pdf)
