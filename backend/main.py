import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sys

# Ensure root path is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.ocr_service import extract_text_from_file
from backend.services.ai_engine import generate_tor_checklist
from backend.services.drive_service import upload_file_to_drive
from extract_tor import generate_excel_from_data
from validate_tor import run_validation_on_file

app = FastAPI(title="TOR Checklist Generator API", version="2.0.0")

# CORS Setup for Vercel / Local Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Flexible Root Path Detection (Works on Windows Local & Linux Render Cloud)
BASE_DIR = r'D:\CBD\TORChecklist' if os.path.exists(r'D:\CBD\TORChecklist') else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATE_PATH = os.path.join(BASE_DIR, 'OutputTORChecklist', 'TOR Checklist template.xlsx')
OUTPUT_DIR = os.path.join(BASE_DIR, 'OutputTORChecklist')
TEMP_DIR = os.path.join(BASE_DIR, 'InputTOR')

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

class LoginRequest(BaseModel):
    email: str
    token: str = None

class ShareRequest(BaseModel):
    email: str
    link: str

@app.post("/api/auth/verify")
def verify_auth(req: LoginRequest):
    """Verifies that the Google Login email ends with @realsmart.co.th"""
    if req.email.endswith("@realsmart.co.th"):
        return {"authenticated": True, "message": f"Welcome {req.email}"}
    else:
        raise HTTPException(status_code=401, detail="Unauthorized: Only realsmart.co.th Google Accounts are allowed.")

@app.post("/api/upload")
async def upload_tor_file(file: UploadFile = File(...)):
    """
    Handles TOR file upload pipeline:
      1. OCR / Text Extraction
      2. AI RAG Extraction (Metadata + Checklist) with Knowledge Base
      3. AI Critic Self-Correction Loop
      4. Generate Excel (New template: Metadata Row 1-3, Data Row 6+)
      5. Validation
      6. Upload to Google Drive / Direct Download Fallback
    """
    file_path = os.path.join(TEMP_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. OCR / Text Extraction
        print(f"[Upload] Extracting text from {file.filename}...")
        text_content = extract_text_from_file(file_path)
        if not text_content or text_content.startswith("[Error"):
            raise HTTPException(status_code=400, detail="Failed to extract text from file.")

        # 2 & 3. AI RAG Extraction + Critic Self-Correction (returns dict with metadata + checklist)
        print("[Upload] Calling AI Engine (RAG + Critic)...")
        ai_result = generate_tor_checklist(text_content)
        
        # Extract metadata and checklist from AI result
        metadata = ai_result.get('metadata', {})
        checklist_items = ai_result.get('checklist', [])

        # 4. Generate Excel File (New template structure)
        output_filename = f"{os.path.splitext(file.filename)[0]}_Checklist.xlsx"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        print(f"[Upload] Generating Excel: {output_filename}...")
        generate_excel_from_data(checklist_items, TEMPLATE_PATH, output_path, metadata=metadata)

        # 5. Validation (Format + Metadata + Data Audit)
        is_valid = run_validation_on_file(output_path)
        if not is_valid:
            print("[Upload] Validation warning: output structure check reported issues.")

        # 6. Upload to Google Drive / Direct Render Server Storage Download Fallback
        print("[Upload] Uploading to Google Drive / Direct Download Fallback...")
        drive_links = upload_file_to_drive(output_path, output_filename)

        return {
            "success": True,
            "filename": output_filename,
            "metadata": metadata,
            "data": checklist_items,
            "webViewLink": drive_links.get("webViewLink"),
            "webContentLink": drive_links.get("webContentLink")
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Upload] Error processing upload: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/api/download/{filename}")
def download_excel_file(filename: str):
    """Directly serves the generated Excel file from Render server storage."""
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found on server.")

@app.post("/api/share/email")
def share_via_email(req: ShareRequest):
    """Mocks or sends email forwarding for demo purposes."""
    print(f"Sharing link {req.link} to email {req.email}")
    return {
        "success": True, 
        "message": f"Successfully shared link to {req.email}",
        "mailto_fallback": f"mailto:{req.email}?subject=TOR%20Checklist%20Shared%20Link&body=Here%20is%20the%20link%20to%20the%20TOR%20Checklist:%20{req.link}"
    }

@app.get("/")
def health_check():
    return {"status": "ok", "service": "TOR Checklist Generator API v2.0 (RAG + Critic)", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
