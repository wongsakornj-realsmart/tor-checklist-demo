import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Flexible Root Path Detection (Works on Windows Local & Linux Render Cloud)
BASE_DIR = r'D:\CBD\TORChecklist' if os.path.exists(r'D:\CBD\TORChecklist') else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SERVICE_ACCOUNT_KEY = os.path.join(BASE_DIR, 'torchecklistagent-105d923c64f7.json')
FOLDER_ID_FILE = os.path.join(BASE_DIR, 'GGFolderAddress.txt')
DEFAULT_FOLDER_ID = "1QJ6roIdY73BTp2WbdyL1EcT4M3mVjRmq"

def get_drive_service():
    """Authenticates and returns the Google Drive service object using Env Var or File."""
    creds = None
    scopes = ['https://www.googleapis.com/auth/drive']

    # 1. Try loading from Environment Variable (Render Cloud)
    env_creds = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if env_creds:
        try:
            creds_info = json.loads(env_creds)
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
            print("Successfully loaded Google Drive Credentials from Environment Variable.")
        except Exception as e:
            print(f"Error parsing GOOGLE_CREDENTIALS_JSON env var: {e}")

    # 2. Try loading from File (Windows Local)
    if not creds and os.path.exists(SERVICE_ACCOUNT_KEY):
        try:
            creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY, scopes=scopes)
            print("Successfully loaded Google Drive Credentials from JSON file.")
        except Exception as e:
            print(f"Error loading credentials from file: {e}")

    if not creds:
        print("Google Drive credentials not found in Env or File. Running in mock mode.")
        return None

    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Failed to build drive service: {e}")
        return None

def upload_file_to_drive(file_path: str, file_name: str) -> dict:
    """
    Uploads a file to the central Google Drive folder and sets permission to anyoneReader.
    Returns a dictionary containing webViewLink and webContentLink.
    """
    mock_response = {
        "webViewLink": "https://drive.google.com/file/d/demo_mock_view_link/view?usp=sharing",
        "webContentLink": "https://drive.google.com/uc?export=download&id=demo_mock_view_link"
    }

    if not os.path.exists(file_path):
        print(f"File to upload not found: {file_path}")
        return mock_response

    service = get_drive_service()
    if not service:
        print("Google Drive service not available, returning mock links.")
        return mock_response

    try:
        # Read Target Folder ID from Env Var first, then File, then Default Backup
        folder_id = os.getenv("GOOGLE_FOLDER_ID", "")
        if not folder_id and os.path.exists(FOLDER_ID_FILE):
            with open(FOLDER_ID_FILE, 'r', encoding='utf-8') as f:
                folder_id = f.read().strip()
        if not folder_id:
            folder_id = DEFAULT_FOLDER_ID
        
        # If Folder ID is a URL, extract the ID
        if "folders/" in folder_id:
            folder_id = folder_id.split("folders/")[-1].split("?")[0]

        file_metadata = {
            'name': file_name,
            'parents': [folder_id] if folder_id else []
        }

        media = MediaFileUpload(file_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)

        file = service.files().create(
            body=file_metadata, media_body=media, fields='id, webViewLink, webContentLink'
        ).execute()

        file_id = file.get('id')

        # Set permission to Anyone with the link can view
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        service.permissions().create(
            fileId=file_id, body=permission
        ).execute()

        # Re-fetch file to get updated links if needed
        updated_file = service.files().get(
            fileId=file_id, fields='id, webViewLink, webContentLink'
        ).execute()

        return {
            "webViewLink": updated_file.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view"),
            "webContentLink": updated_file.get('webContentLink', f"https://drive.google.com/uc?export=download&id={file_id}")
        }

    except Exception as e:
        print(f"Error uploading file to Google Drive: {e}")
        return mock_response
