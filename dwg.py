import streamlit as st
import os
import tempfile
import zipfile
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

st.set_page_config(page_title="Uploader FAT Splitter", layout="centered")
st.title("📡 Uploader FAT Splitter")

# Folder tujuan Google Drive
GDRIVE_FOLDERS = {
    "DISTRIBUTION CABLE": "1XkWqvRX4SUYMrtMQ7vt8197oSja4r9p-",
    "BOUNDARY CLUSTER": "1IMpaQWnpG8c8P5j3phUMP1G9zTPBDQMi",
    "CABLE": "16aesqK-OIqYIDAIn_ymLzf1-VkLyXonl"
}

# Ambil credentials dari Streamlit secrets
def get_credentials():
    return Credentials(
        token=None,
        refresh_token=st.secrets["google"]["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=st.secrets["google"]["client_id"],
        client_secret=st.secrets["google"]["client_secret"],
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )

# Fungsi upload
def save_and_upload(kmz_file, folder_keys, service):
    if kmz_file:
        temp_dir = tempfile.mkdtemp()
        kmz_path = os.path.join(temp_dir, kmz_file.name)
        with open(kmz_path, "wb") as f:
            f.write(kmz_file.getbuffer())

        new_filename = kmz_file.name.replace(".kmz", ".kml")
        with zipfile.ZipFile(kmz_path, 'r') as zip_ref:
            for file_name in zip_ref.namelist():
                if file_name.endswith(".kml"):
                    zip_ref.extract(file_name, temp_dir)
                    kml_path = os.path.join(temp_dir, file_name)

                    for key in folder_keys:
                        folder_id = GDRIVE_FOLDERS[key]
                        file_metadata = {'name': new_filename, 'parents': [folder_id]}
                        media = MediaFileUpload(kml_path, mimetype='application/vnd.google-earth.kml+xml')
                        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                        st.success(f"✅ Berhasil upload ke folder {key}")

# Upload input
uploaded_cluster = st.file_uploader("📄 Upload file .KMZ CLUSTER (berisi FAT & NEW POLE)", type=["kmz"])
uploaded_subfeeder = st.file_uploader("📄 Upload file .KMZ SUBFEEDER (berisi NEW POLE 7-4 / 9-4)", type=["kmz"])

if st.button("🚀 Upload ke Google Drive"):
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    st.info("📤 Memproses file KMZ Cluster...")
    save_and_upload(uploaded_cluster, ["DISTRIBUTION CABLE", "BOUNDARY CLUSTER"], service)

    st.info("📤 Memproses file KMZ Subfeeder...")
    save_and_upload(uploaded_subfeeder, ["CABLE"], service)
