import streamlit as st
import zipfile
import tempfile
import os
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Konfigurasi halaman
st.set_page_config(page_title="Uploader FAT Splitter", layout="centered")
st.title("📡 Uploader FAT Splitter")

# File upload
uploaded_cluster = st.file_uploader("📄 Upload file .KMZ CLUSTER (berisi FAT & NEW POLE)", type=["kmz"])
uploaded_subfeeder = st.file_uploader("📄 Upload file .KMZ SUBFEEDER (berisi NEW POLE 7-4 / 9-4)", type=["kmz"])
submit_clicked = st.button("🚀 Upload ke Google Drive")

# Folder tujuan Google Drive
GDRIVE_FOLDERS = {
    "DISTRIBUTION CABLE": "1XkWqvRX4SUYMrtMQ7vt8197oSja4r9p-",
    "BOUNDARY CLUSTER": "1IMpaQWnpG8c8P5j3phUMP1G9zTPBDQMi",
    "CABLE": "16aesqK-OIqYIDAIn_ymLzf1-VkLyXonl"
}

SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Simpan kredensial antar sesi
if "creds" not in st.session_state:
    st.session_state.creds = None


def get_drive_service():
    creds = None

    # 1. Coba load token.json dari local
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # 2. Cek jika token tidak valid, refresh jika bisa
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open("token.json", "w") as token_file:
                token_file.write(creds.to_json())
            st.success("🔄 Token diperbarui.")
        except Exception as e:
            st.error(f"❌ Gagal refresh token: {e}")
            creds = None

    # 3. Jika belum login sama sekali, minta login
    if not creds or not creds.valid:
        flow = Flow.from_client_secrets_file(
            "credentials.json",
            scopes=SCOPES,
            redirect_uri="https://tara-capslock.streamlit.app/"
        )

        auth_url, _ = flow.authorization_url(prompt='consent')

        st.markdown(f"🔐 [Klik untuk login dengan Google (buka tab baru)]({auth_url})", unsafe_allow_html=True)
        auth_code = st.text_input("📥 Masukkan kode otentikasi dari Google di sini:", key="auth_code_input")

        if auth_code:
            try:
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
                with open("token.json", "w") as token_file:
                    token_file.write(creds.to_json())
                st.success("✅ Login berhasil! Token disimpan.")
            except Exception as e:
                st.error(f"❌ Gagal login: {e}")
                return None

    # Simpan ke session state
    if creds:
        st.session_state.creds = creds
        return build("drive", "v3", credentials=creds)

    return None


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


def upload_kml_to_drive(kml_path, new_filename, folder_ids):
    # Pastikan hanya satu kali login
    if not st.session_state.creds:
        service = get_drive_service()
    else:
        service = build("drive", "v3", credentials=st.session_state.creds)

    if not service:
        st.warning("⚠️ Silakan login terlebih dahulu sebelum upload.")
        return

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


# Proses utama saat tombol ditekan
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
