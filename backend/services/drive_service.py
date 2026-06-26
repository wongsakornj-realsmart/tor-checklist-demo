import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Path configurations defined by USER
SERVICE_ACCOUNT_KEY = r'D:\CBD\TORChecklist\torchecklistagent-105d923c64f7.json'
FOLDER_ID_FILE = r'D:\CBD\TORChecklist\GGFolderAddress.txt'

def get_drive_service():
    """Authenticates and returns the Google Drive service object."""
    if not os.path.exists(SERVICE_ACCOUNT_KEY):
        print(f"Service account key not found at {SERVICE_ACCOUNT_KEY}. Running in mock mode.")
        return None

    try:
        scopes = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_KEY, scopes=scopes
        )
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
        # Read Target Folder ID
        folder_id = ""
        if os.path.exists(FOLDER_ID_FILE):
            with open(FOLDER_ID_FILE, 'r', encoding='utf-8') as f:
                folder_id = f.read().strip()
        
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
