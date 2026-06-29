import os
import sys
import json
import traceback

# Force stdout to UTF-8 to prevent Windows console cp874 charmap errors
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, r'D:\CBD\TORChecklist')

from backend.services.ocr_service import extract_text_from_file
from backend.services.ai_engine import generate_tor_checklist
from extract_tor import generate_excel_from_data
from validate_tor import run_validation_on_file

def run_tester():
    files_to_test = [
        r"D:\DGA\Attach_TOR_1.pdf",
        r"C:\Users\womgsakorn_j\Documents\SME D Bank\Final\00_Reference_TOR\2_ขอบเขตของงาน.pdf"
    ]
    
    BASE_DIR = r'D:\CBD\TORChecklist'
    TEMPLATE_PATH = os.path.join(BASE_DIR, 'OutputTORChecklist', 'TOR Checklist template.xlsx')
    OUTPUT_DIR = os.path.join(BASE_DIR, 'OutputTORChecklist')
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("===================================================================")
    print("        STARTING SYSTEM TESTER (E2E AUTOMATED AUDIT)        ")
    print("===================================================================")

    for idx, file_path in enumerate(files_to_test, 1):
        print(f"\n\n===================================================================")
        print(f" TEST # {idx}: {file_path}")
        print(f"===================================================================")
        
        if not os.path.exists(file_path):
            print(f"[Error] File does not exist on filesystem: {file_path}")
            continue
            
        file_size = os.path.getsize(file_path)
        print(f"[Tester] File found. Size: {file_size / 1024:.2f} KB")

        try:
            # 1. OCR / Text Extraction
            print(f"\n[Step 1] Extracting text from PDF...")
            text_content = extract_text_from_file(file_path)
            print(f"[Tester] Extracted {len(text_content)} characters.")
            if len(text_content) > 0:
                print(f"[Tester] Text Sample Preview:\n{text_content[:300]}...\n")

            # 2. AI Engine (Metadata + RAG + Critic + Sorting + Polish)
            print(f"\n[Step 2] Executing AI Engine (RAG + Critic + Natural Sort + Polish)...")
            ai_result = generate_tor_checklist(text_content)
            
            metadata = ai_result.get('metadata', {})
            checklist = ai_result.get('checklist', [])
            
            print(f"\n[Tester] === AI Extraction Summary ===")
            print(f"  * Project Name: {metadata.get('project_name')}")
            print(f"  * Client Name:  {metadata.get('client_name')}")
            print(f"  * Dateline:     {metadata.get('dateline')}")
            print(f"  * Total Items Extracted: {len(checklist)} rows")

            if len(checklist) > 0:
                print(f"\n[Tester] === Sample 3 Extracted Items (Auditing Granularity & Fields) ===")
                for item_idx, item in enumerate(checklist[:3], 1):
                    print(f"\n  [Item {item_idx}]")
                    print(f"    - ลำดับ: {item.get('ลำดับ')}")
                    print(f"    - หมวดหมู่หลัก: {item.get('หมวดหมู่หลัก')}")
                    print(f"    - ข้อกำหนด: {item.get('ข้อกำหนด / รายละเอียด (Requirement / Details)')[:120]}...")
                    print(f"    - ชื่อเอกสารที่ใช้ยื่น: {item.get('ชื่อเอกสารที่ใช้ยื่น')}")
                    print(f"    - รายละเอียดที่ต้องระบุ: {item.get('รายละเอียดที่ต้องระบุ')}")
            else:
                print(f"[Tester][Error] Checklist extraction returned 0 items!!!")

            # 3. Generate Excel
            output_filename = f"TEST_{idx}_{os.path.splitext(os.path.basename(file_path))[0]}_Checklist.xlsx"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            print(f"\n[Step 3] Generating Excel File: {output_path}...")
            generate_excel_from_data(checklist, TEMPLATE_PATH, output_path, metadata=metadata)
            
            if os.path.exists(output_path):
                print(f"[Tester] Excel generated successfully. Size: {os.path.getsize(output_path) / 1024:.2f} KB")
            else:
                print(f"[Tester][Error] Excel file not found at expected path!!!")

            # 4. Run Validation
            print(f"\n[Step 4] Running Format & Structure Validation...")
            is_valid = run_validation_on_file(output_path)
            print(f"[Tester] Validation Status: {'PASSED' if is_valid else 'WARNING'}")

            print(f"\n>>>>> TEST # {idx} COMPLETED SUCCESSFULLY <<<<<")

        except Exception as e:
            print(f"\n[Tester][FATAL ERROR] Test #{idx} failed with exception:")
            traceback.print_exc()

if __name__ == "__main__":
    run_tester()
