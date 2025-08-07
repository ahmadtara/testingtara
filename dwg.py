import streamlit as st
import zipfile
import tempfile
import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

st.set_page_config(page_title="Uploader FAT Splitter", layout="centered")
st.title("📡 Uploader FAT Splitter")

uploaded_cluster = st.file_uploader("📄 Upload file .KMZ CLUSTER (berisi FAT & NEW POLE)", type=["kmz"])
uploaded_subfeeder = st.file_uploader("📄 Upload file .KMZ SUBFEEDER (berisi NEW POLE 7-4 / 9-4)", type=["kmz"])
submit_clicked = st.button("🚀 Upload ke Google Drive")

# Folder tujuan Google Drive
GDRIVE_FOLDERS = {
    "DISTRIBUTION CABLE": "1XkWqvRX4SUYMrtMQ7vt8197oSja4r9p-",
    "BOUNDARY CLUSTER": "1IMpaQWnpG8c8P5j3phUMP1G9zTPBDQMi",
    "CABLE": "16aesqK-OIqYIDAIn_ymLzf1-VkLyXonl"
}

# Scope minimum untuk akses file di Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    creds = None
    if os.path.exists("token.pkl"):
        with open("token.pkl", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            st.warning("🔐 Buka URL login Google yang muncul di terminal dan tempelkan kode verifikasi.")
            creds = flow.run_console()  # Pakai login manual
        with open("token.pkl", "wb") as token:
            pickle.dump(creds, token)

    return build("drive", "v3", credentials=creds)

def extract_kml_from_kmz(kmz_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kmz") as tmp_kmz:
        tmp_kmz.write(kmz_file.read())
        kmz_path = tmp_kmz.name

    with zipfile.ZipFile(kmz_path, 'r') as zf:
        kml_filename = next((f for f in zf.namelist() if f.lower().endswith(".kml")), None)
        if not kml_filename:
            st.error("❌ File .kml tidak ditemukan di dalam .kmz.")
            return None, None

        with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as tmp_kml:
            tmp_kml.write(zf.read(kml_filename))
            return tmp_kml.name, os.path.splitext(os.path.basename(kmz_path))[0] + ".kml"

def upload_kml_to_drive_oauth(kml_path, new_filename, folder_ids):
    service = get_drive_service()
    for folder_id in folder_ids:
        file_metadata = {
            'name': new_filename,
            'parents': [folder_id]
        }
        media = MediaFileUpload(kml_path, mimetype='application/vnd.google-earth.kml+xml')
        try:
            service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            st.success(f"✅ File {new_filename} berhasil diupload ke folder ID: {folder_id}")
        except Exception as e:
            st.error(f"❌ Gagal upload ke folder ID: {folder_id}\n{e}")

if submit_clicked:
    if uploaded_cluster:
        st.info("📤 Memproses file KMZ Cluster...")
        kml_path, new_filename = extract_kml_from_kmz(uploaded_cluster)
        if kml_path:
            upload_kml_to_drive_oauth(kml_path, new_filename, [
                GDRIVE_FOLDERS["DISTRIBUTION CABLE"],
                GDRIVE_FOLDERS["BOUNDARY CLUSTER"]
            ])

    if uploaded_subfeeder:
        st.info("📤 Memproses file KMZ Subfeeder...")
        kml_path, new_filename = extract_kml_from_kmz(uploaded_subfeeder)
        if kml_path:
            upload_kml_to_drive_oauth(kml_path, new_filename, [
                GDRIVE_FOLDERS["CABLE"]
            ])
