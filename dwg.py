import streamlit as st
import zipfile
import tempfile
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

st.set_page_config(page_title="Uploader FAT Splitter", layout="centered")
st.title("📡 Uploader FAT Splitter")

# Upload file
uploaded_cluster = st.file_uploader("📄 Upload file .KMZ CLUSTER (berisi FAT & NEW POLE)", type=["kmz"])
uploaded_subfeeder = st.file_uploader("📄 Upload file .KMZ SUBFEEDER (berisi NEW POLE 7-4 / 9-4)", type=["kmz"])

submit_clicked = st.button("🚀 Upload ke Google Drive")

# Folder tujuan Google Drive
GDRIVE_FOLDERS = {
    "DISTRIBUTION CABLE": "1XkWqvRX4SUYMrtMQ7vt8197oSja4r9p-",
    "BOUNDARY CLUSTER": "1IMpaQWnpG8c8P5j3phUMP1G9zTPBDQMi",
    "CABLE": "16aesqK-OIqYIDAIn_ymLzf1-VkLyXonl"
}

# Fungsi upload ke Google Drive
def upload_kml_to_drive(kml_path, new_filename, folder_ids):
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=['https://www.googleapis.com/auth/drive']
    )
    drive_service = build('drive', 'v3', credentials=creds)

    for folder_id in folder_ids:
        file_metadata = {
            'name': new_filename,
            'parents': [folder_id]
        }
        media = MediaFileUpload(kml_path, mimetype='application/vnd.google-earth.kml+xml')

        try:
            drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            st.success(f"✅ File {new_filename} berhasil diupload ke folder ID: {folder_id}")
        except HttpError as error:
            st.error(f"❌ Gagal upload ke folder ID: {folder_id}\n{error}")
