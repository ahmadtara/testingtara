import streamlit as st
import os
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

st.set_page_config(page_title="Uploader FAT Splitter", layout="centered")
st.title("📡 Uploader FAT Splitter (Tanpa Login)")

# Folder tujuan Google Drive
GDRIVE_FOLDERS = {
    "DISTRIBUTION CABLE": "1XkWqvRX4SUYMrtMQ7vt8197oSja4r9p-",
    "BOUNDARY CLUSTER": "1IMpaQWnpG8c8P5j3phUMP1G9zTPBDQMi",
    "CABLE": "16aesqK-OIqYIDAIn_ymLzf1-VkLyXonl"
}

# Load credential service account (pastikan file kunci sudah diupload di folder proyek)
SERVICE_ACCOUNT_FILE = "service_account_credentials.json"  # ganti dengan nama file JSON kamu

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Inisialisasi service Google Drive
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=credentials)

def upload_to_drive(file_path, filename, folder_ids):
    for folder_id in folder_ids:
        file_metadata = {
            "name": filename,
            "parents": [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype="application/vnd.google-earth.kmz")

        try:
            uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            st.success(f"✅ File '{filename}' berhasil diupload ke folder ID: {folder_id}")
        except Exception as e:
            st.error(f"❌ Gagal upload ke folder ID: {folder_id}\n{e}")

# UI upload file
uploaded_file = st.file_uploader("📄 Upload file .KMZ CLUSTER", type=["kmz"])
if uploaded_file:
    filename = uploaded_file.name
    temp_kmz = os.path.join(tempfile.gettempdir(), filename)
    with open(temp_kmz, "wb") as f:
        f.write(uploaded_file.read())

    if st.button("🚀 Upload ke Google Drive"):
        upload_to_drive(temp_kmz, filename, [
            GDRIVE_FOLDERS["DISTRIBUTION CABLE"],
            GDRIVE_FOLDERS["BOUNDARY CLUSTER"],
            GDRIVE_FOLDERS["CABLE"]
        ])
