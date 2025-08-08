import streamlit as st
import zipfile
import os
import tempfile
import shutil
import xml.etree.ElementTree as ET
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# SCOPES dan file kredensial
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRET_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# Folder tujuan Google Drive
GDRIVE_FOLDERS = {
    "DISTRIBUTION CABLE": "1XkWqvRX4SUYMrtMQ7vt8197oSja4r9p-",
    "BOUNDARY CLUSTER": "1IMpaQWnpG8c8P5j3phUMP1G9zTPBDQMi",
    "CABLE": "16aesqK-OIqYIDAIn_ymLzf1-VkLyXonl"
}

def save_token(creds):
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

def load_token():
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_token(creds)
        return creds
    return None

def get_drive_service():
    creds = load_token()
    if creds:
        return build('drive', 'v3', credentials=creds)

    # OAuth alur
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri="https://tara-capslock.streamlit.app/"
    )

    query_params = st.query_params

    if "code" in query_params:
        try:
            code = query_params["code"]
            flow.fetch_token(code=code)
            creds = flow.credentials
            save_token(creds)
            st.success("✅ Autentikasi berhasil! Anda sekarang dapat mengupload file.")
            st.experimental_rerun()
        except Exception as e:
            st.error("❌ Gagal mendapatkan token autentikasi.")
            st.exception(e)
            st.stop()

    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
    st.warning("🔐 Anda perlu login terlebih dahulu dengan akun Google Anda.")
    st.markdown(f"[👉 Klik di sini untuk login dengan Google]({auth_url})", unsafe_allow_html=True)
    st.stop()

def convert_kmz_to_kml(kmz_file, output_name):
    with tempfile.TemporaryDirectory() as tmpdirname:
        kmz_path = os.path.join(tmpdirname, kmz_file.name)
        with open(kmz_path, "wb") as f:
            f.write(kmz_file.read())
        with zipfile.ZipFile(kmz_path, 'r') as z:
            z.extractall(tmpdirname)
            for root, dirs, files in os.walk(tmpdirname):
                for file in files:
                    if file.endswith(".kml"):
                        extracted_path = os.path.join(root, file)
                        final_path = os.path.join(tempfile.gettempdir(), output_name)
                        shutil.copy2(extracted_path, final_path)
                        return final_path
    return None

def upload_kml_to_drive(kml_path, filename, folder_ids):
    if not os.path.exists(kml_path):
        st.error(f"❌ File tidak ditemukan: {kml_path}")
        return

    try:
        service = get_drive_service()
        if not service:
            st.error("❌ Gagal mendapatkan layanan Google Drive.")
            return

        for folder_id in folder_ids:
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            media = MediaFileUpload(kml_path, mimetype='application/vnd.google-earth.kml+xml')
            uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            st.success(f"✅ File '{filename}' berhasil diupload ke folder ID: {folder_id}")

    except HttpError as error:
        st.error("❌ Terjadi kesalahan saat mengunggah ke Google Drive.")
        st.exception(error)
    except Exception as e:
        st.error("❌ Terjadi kesalahan tak terduga.")
        st.exception(e)

# UI Streamlit
st.title("📤 Upload KMZ ke Google Drive")

uploaded_cluster = st.file_uploader("📄 Upload file .KMZ CLUSTER (berisi FAT & NEW POLE)", type=["kmz"], key="cluster")
uploaded_subfeeder = st.file_uploader("📄 Upload file .KMZ SUBFEEDER (berisi NEW POLE 7-4 / 9-4)", type=["kmz"], key="subfeeder")
submit_clicked = st.button("🚀 Upload ke Google Drive")

if submit_clicked:
    if uploaded_cluster:
        new_filename = uploaded_cluster.name.replace(".kmz", ".kml")
        kml_path = convert_kmz_to_kml(uploaded_cluster, new_filename)
        if kml_path:
            upload_kml_to_drive(kml_path, new_filename, [
                GDRIVE_FOLDERS["DISTRIBUTION CABLE"],
                GDRIVE_FOLDERS["BOUNDARY CLUSTER"]
            ])
        else:
            st.error("❌ Gagal mengonversi KMZ CLUSTER ke KML.")

    if uploaded_subfeeder:
        new_filename = uploaded_subfeeder.name.replace(".kmz", ".kml")
        kml_path = convert_kmz_to_kml(uploaded_subfeeder, new_filename)
        if kml_path:
            upload_kml_to_drive(kml_path, new_filename, [
                GDRIVE_FOLDERS["CABLE"]
            ])
        else:
            st.error("❌ Gagal mengonversi KMZ SUBFEEDER ke KML.")
