import streamlit as st
import os
import tempfile
import zipfile
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

st.title("Uploader FAT Splitter dengan Kode Otorisasi")

# File client secret kamu
CLIENT_SECRETS_FILE = "client_secret.json"

SCOPES = ['https://www.googleapis.com/auth/drive.file']
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'  # atau sesuai redirect URI yang dipakai

# Tempat simpan credentials token
TOKEN_FILE = "token.json"

def get_drive_service_from_auth_code(auth_code):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=auth_code)
    creds = flow.credentials
    service = build('drive', 'v3', credentials=creds)
    return service, creds

def extract_kml_from_kmz(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kmz") as tmp_kmz:
        tmp_kmz.write(uploaded_file.read())
        kmz_path = tmp_kmz.name
    with zipfile.ZipFile(kmz_path, 'r') as zf:
        kml_file = next((f for f in zf.namelist() if f.endswith('.kml')), None)
        if not kml_file:
            st.error("File .kml tidak ditemukan di dalam .kmz")
            return None, None
        with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as tmp_kml:
            tmp_kml.write(zf.read(kml_file))
            return tmp_kml.name, os.path.basename(kml_file)

def upload_file_to_drive(service, file_path, filename, folder_ids):
    for folder_id in folder_ids:
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='application/vnd.google-earth.kml+xml')
        try:
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            st.success(f"File '{filename}' berhasil diupload ke folder {folder_id}")
        except Exception as e:
            st.error(f"Gagal upload ke folder {folder_id}: {e}")

# Masukkan kode otorisasi kamu di sini (hardcode atau input)
auth_code = st.text_input("Masukkan kode otorisasi Google OAuth:", value="4/0AVMBsJhZzxjZxWvXX2eox6vYECjdtsh7KCZ4UKOhQEnICbmNBRAi8lL0OO40t_l7g8D-cw")

uploaded_file = st.file_uploader("Upload file .KMZ", type=['kmz'])
if st.button("Upload"):
    if not auth_code:
        st.error("Masukkan kode otorisasi terlebih dahulu!")
    elif not uploaded_file:
        st.error("Upload file .kmz terlebih dahulu!")
    else:
        try:
            service, creds = get_drive_service_from_auth_code(auth_code)
            kml_path, kml_name = extract_kml_from_kmz(uploaded_file)
            if kml_path:
                folder_ids = [
                    "1XkWqvRX4SUYMrtMQ7vt8197oSja4r9p-",  # DISTRIBUTION CABLE
                    "1IMpaQWnpG8c8P5j3phUMP1G9zTPBDQMi",  # BOUNDARY CLUSTER
                    "16aesqK-OIqYIDAIn_ymLzf1-VkLyXonl"   # CABLE
                ]
                upload_file_to_drive(service, kml_path, kml_name, folder_ids)
        except Exception as e:
            st.error(f"Error saat upload: {e}")
