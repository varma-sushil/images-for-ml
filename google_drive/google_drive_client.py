from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import logging
import os


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def authenticate_drive(cred_file):
    """
    Authenticate Google Drive API using a service account.
    """

    try:
        credentials = service_account.Credentials.from_service_account_file(
            cred_file,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive_service = build('drive', 'v3', credentials=credentials)
        logging.info("Google Drive authentication successful.")
        print("Google Drive authentication successful.")
        return drive_service
    except Exception as e:
        logging.error(f"Failed to authenticate Google Drive: {e}")
        print(f"Failed to authenticate Google Drive: {e}")
        return None


def get_or_create_gd_folder(service, folder_name, parent_id=None):
    """
    Get or create a Google Drive folder by name, within an optional parent folder.
    """
    # Query to check if folder exists
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=10
        ).execute()

        # If folder exists, return its ID
        files = results.get('files', [])
        if files:
            logging.info(f"Folder '{folder_name}' exists with ID: {files[0]['id']}")
            print(f"Folder '{folder_name}' already exists with ID: {files[0]['id']}")
            return files[0]['id']

        # If folder does not exist, create it
        logging.info(f"Creating folder '{folder_name}'...")
        print(f"Creating folder '{folder_name}'...")
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            folder_metadata['parents'] = [parent_id]

        folder = service.files().create(body=folder_metadata, fields='id').execute()
        logging.info(f"Folder '{folder_name}' created with ID: {folder.get('id')}")
        print(f"Folder '{folder_name}' created with ID: {folder.get('id')}")
        return folder.get('id')
    except Exception as e:
        logging.error(f"Error in creating/getting folder '{folder_name}': {e}")
        print(f"Error in creating/getting folder '{folder_name}': {e}")
        return None


def upload_file(service, file_path, folder_id):
    """
    Upload a file to Google Drive, within a specific folder.
    """
    try:
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info(f"File uploaded successfully: {file_path}")
        print(f"File uploaded successfully: {file_path}")
        return file.get('id')
    except Exception as e:
        logging.error(f"Failed to upload file {file_path}: {e}")
        print(f"Failed to upload file {file_path}: {e}")
        return None


# Usage
if __name__ == "__main__":

    current_directory = os.getcwd()
    service_account_creds = os.path.join(current_directory, 'image-project-441409-14ab96bd49d0.json')

    drive_service = authenticate_drive(service_account_creds)

    # Example usage: Create a folder and upload a file
    folder_id = get_or_create_gd_folder(drive_service, "My New Folder", parent_id='1-30we5O6YunT9vK8je5YMHOSdyYUFAqD')
    file_id = upload_file(drive_service, os.path.join(current_directory, "test.json"), folder_id)
    print("Uploaded file ID:", file_id)
