import streamlit as st
import zipfile
import tempfile
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
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

        drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

    st.success(f"✅ File {new_filename} berhasil diupload ke folder tujuan.")

# Fungsi ekstrak file .kml dari .kmz
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

# Jalankan jika tombol diklik
if submit_clicked:
    if uploaded_cluster:
        st.info("📤 Memproses file KMZ Cluster...")
        kml_path, new_filename = extract_kml_from_kmz(uploaded_cluster)
        if kml_path:
            upload_kml_to_drive(kml_path, new_filename, [
                GDRIVE_FOLDERS["DISTRIBUTION CABLE"],
                GDRIVE_FOLDERS["BOUNDARY CLUSTER"]
            ])

    if uploaded_subfeeder:
        st.info("📤 Memproses file KMZ Subfeeder...")
        kml_path, new_filename = extract_kml_from_kmz(uploaded_subfeeder)
        if kml_path:
            upload_kml_to_drive(kml_path, new_filename, [
                GDRIVE_FOLDERS["CABLE"]
            ])
