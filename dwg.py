import streamlit as st
import os
import tempfile
import zipfile
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

st.set_page_config(page_title="Uploader FAT Splitter", layout="centered")
st.title("📡 Uploader FAT Splitter")

# Folder Google Drive tujuan
GDRIVE_FOLDERS = {
    "DISTRIBUTION CABLE": "1XkWqvRX4SUYMrtMQ7vt8197oSja4r9p-",
    "BOUNDARY CLUSTER": "1IMpaQWnpG8c8P5j3phUMP1G9zTPBDQMi",
    "CABLE": "16aesqK-OIqYIDAIn_ymLzf1-VkLyXonl"
}

# Inisialisasi Flow
CLIENT_SECRET_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"  # biar dapet kode otorisasi manual

flow = Flow.from_client_secrets_file(
    CLIENT_SECRET_FILE,
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)

auth_url, _ = flow.authorization_url(prompt='consent')

# ⬅️ TOMBOL LOGIN
st.markdown("## 🔐 Login Google Drive")
st.markdown(f"[Klik untuk login dengan Google]({auth_url})", unsafe_allow_html=True)
auth_code = st.text_input("Tempelkan kode otorisasi dari Google di sini:")

creds = None
if st.button("✅ Submit Kode"):
    if auth_code:
        try:
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            st.success("Login berhasil! ✅ Sekarang kamu bisa upload.")
        except Exception as e:
            st.error(f"Gagal login: {e}")

# 🔼 Upload file
uploaded_cluster = st.file_uploader("📄 Upload file .KMZ CLUSTER (berisi FAT & NEW POLE)", type=["kmz"])
uploaded_subfeeder = st.file_uploader("📄 Upload file .KMZ SUBFEEDER (berisi NEW POLE 7-4 / 9-4)", type=["kmz"])

if st.button("🚀 Upload ke Google Drive") and creds:
    service = build('drive', 'v3', credentials=creds)

    def save_and_upload(kmz_file, folder_keys):
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

    st.info("📤 Memproses file KMZ Cluster...")
    save_and_upload(uploaded_cluster, ["DISTRIBUTION CABLE", "BOUNDARY CLUSTER"])

    st.info("📤 Memproses file KMZ Subfeeder...")
    save_and_upload(uploaded_subfeeder, ["CABLE"])
