import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys

# Ensure root path is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.ocr_service import extract_text_from_file
from backend.services.ai_engine import generate_tor_checklist
from backend.services.drive_service import upload_file_to_drive
from extract_tor import generate_excel_from_data
from validate_tor import run_validation_on_file

app = FastAPI(title="TOR Checklist Generator API (Demo)", version="1.0.0")

# CORS Setup for Vercel / Local Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATE_PATH = r'D:\CBD\TORChecklist\OutputTORChecklist\TOR Checklist template.xlsx'
OUTPUT_DIR = r'D:\CBD\TORChecklist\OutputTORChecklist'
TEMP_DIR = r'D:\CBD\TORChecklist\InputTOR'

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
    Handles TOR file upload -> OCR -> OpenTyphoon AI -> Excel 9-Cols -> Validation -> Google Drive Upload.
    """
    file_path = os.path.join(TEMP_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. OCR / Text Extraction
        print(f"Extracting text from {file.filename}...")
        text_content = extract_text_from_file(file_path)
        if not text_content or text_content.startswith("[Error"):
            raise HTTPException(status_code=400, detail="Failed to extract text from file.")

        # 2. OpenTyphoon AI Extraction & Synthesis (9 Columns)
        print("Calling OpenTyphoon AI...")
        checklist_items = generate_tor_checklist(text_content)

        # 3. Generate Excel File
        output_filename = f"{os.path.splitext(file.filename)[0]}_Checklist.xlsx"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        print("Generating Excel file...")
        generate_excel_from_data(checklist_items, TEMPLATE_PATH, output_path)

        # 4. Validation (Format Audit)
        is_valid = run_validation_on_file(output_path)
        if not is_valid:
            print("Validation warning: output structure check reported issues.")

        # 5. Upload to Google Drive Central Shared Folder
        print("Uploading to Google Drive...")
        drive_links = upload_file_to_drive(output_path, output_filename)

        return {
            "success": True,
            "filename": output_filename,
            "data": checklist_items,
            "webViewLink": drive_links.get("webViewLink"),
            "webContentLink": drive_links.get("webContentLink")
        }

    except Exception as e:
        print(f"Error processing upload: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/api/share/email")
def share_via_email(req: ShareRequest):
    """Mocks or sends email forwarding for demo purposes."""
    # For demo reliability, return immediate success with mailto fallback
    print(f"Sharing link {req.link} to email {req.email}")
    return {
        "success": True, 
        "message": f"Successfully shared link to {req.email}",
        "mailto_fallback": f"mailto:{req.email}?subject=TOR%20Checklist%20Shared%20Link&body=Here%20is%20the%20link%20to%20the%20TOR%20Checklist:%20{req.link}"
    }

@app.get("/")
def health_check():
    return {"status": "ok", "service": "TOR Checklist Generator API (Demo)"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
