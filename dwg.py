import streamlit as st
import os
import zipfile
import tempfile
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import Flow

st.set_page_config(page_title="Uploader FAT Splitter", layout="centered")
st.title("📡 Uploader FAT Splitter")

# Folder tujuan Google Drive
GDRIVE_FOLDERS = {
    "DISTRIBUTION CABLE": "1XkWqvRX4SUYMrtMQ7vt8197oSja4r9p-",
    "BOUNDARY CLUSTER": "1IMpaQWnpG8c8P5j3phUMP1G9zTPBDQMi",
    "CABLE": "16aesqK-OIqYIDAIn_ymLzf1-VkLyXonl"
}

# Simpan kredensial login pengguna
if "credentials" not in st.session_state:
    st.session_state.credentials = None

# Fungsi login OAuth
def login_with_google():
    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=["https://www.googleapis.com/auth/drive.file"],
        redirect_uri="https://tara-capslock.streamlit.app/"
    )
    auth_url, _ = flow.authorization_url(prompt="consent")

    st.markdown(f"[🔐 Klik di sini untuk login Google]({auth_url})", unsafe_allow_html=True)
    auth_code = st.text_input("📥 Tempelkan kode otorisasi dari Google:")

    if auth_code:
        try:
            flow.fetch_token(code=auth_code)
            st.session_state.credentials = flow.credentials
            st.success("✅ Login berhasil!")
        except Exception as e:
            st.error(f"❌ Gagal login: {e}")

# Fungsi upload ke Google Drive
def upload_to_drive(file_path, filename, folder_ids):
    creds = st.session_state.credentials
    if not creds or not creds.valid:
        st.error("❌ Anda belum login Google.")
        return

    service = build("drive", "v3", credentials=creds)

    for folder_id in folder_ids:
        file_metadata = {
            "name": filename,
            "parents": [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype="application/vnd.google-earth.kmz")

        try:
            uploaded = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            st.success(f"✅ File '{filename}' berhasil diupload ke folder ID: {folder_id}")
        except Exception as e:
            st.error(f"❌ Gagal upload ke folder ID: {folder_id}\n{e}")

# UI login
st.subheader("🔐 Login Google Drive")
login_with_google()

# Jika sudah login, tampilkan form upload
if st.session_state.credentials:
    st.subheader("📤 Upload file .KMZ")

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
                GDRIVE_FOLDERS["CABLE"]  # ✅ Sekarang termasuk juga folder CABLE
            ])
