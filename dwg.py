import streamlit as st
import zipfile
import os
import tempfile
import shutil
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

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri="https://tara-capslock.streamlit.app/"
    )

    query_params = st.query_params

    if "code" in query_params:
        code = query_params["code"]
        flow.fetch_token(code=code)
        creds = flow.credentials
        save_token(creds)
        st.success("✅ Autentikasi berhasil! Silakan klik ulang tombol upload.")
        st.rerun()

    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
    st.markdown(f"[🔐 Klik untuk login dengan Google]({auth_url})", unsafe_allow_html=True)
    st.stop()

def extract_and_merge_kmls_from_kmz(kmz_file, target_folder_name, output_name):
    with tempfile.TemporaryDirectory() as tmpdirname:
        kmz_path = os.path.join(tmpdirname, kmz_file.name)
        with open(kmz_path, "wb") as f:
            f.write(kmz_file.read())

        with zipfile.ZipFile(kmz_path, 'r') as z:
            z.extractall(tmpdirname)

        kml_paths = []
        for root, dirs, files in os.walk(tmpdirname):
            if target_folder_name.lower() in root.lower():
                for file in files:
                    if file.endswith(".kml"):
                        kml_paths.append(os.path.join(root, file))

        if not kml_paths:
            return None

        combined_path = os.path.join(tempfile.gettempdir(), output_name)
        with open(combined_path, "w", encoding="utf-8") as outfile:
            for i, path in enumerate(kml_paths):
                with open(path, "r", encoding="utf-8") as infile:
                    content = infile.read()
                    if i == 0:
                        outfile.write(content)
                    else:
                        placemarks = []
                        inside = False
                        for line in content.splitlines():
                            if "<Placemark" in line:
                                inside = True
                            if inside:
                                placemarks.append(line)
                            if "</Placemark>" in line:
                                inside = False
                        outfile.write("\n".join(placemarks) + "\n")
            outfile.write("</Document>\n</kml>")

        return combined_path

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
    base_cluster_name = uploaded_cluster.name.replace(".kmz", "") if uploaded_cluster else None
    base_subfeeder_name = uploaded_subfeeder.name.replace(".kmz", "") if uploaded_subfeeder else None

    if uploaded_cluster:
        kml_dc = extract_and_merge_kmls_from_kmz(uploaded_cluster, "DISTRIBUTION CABLE", base_cluster_name + "_DC.kml")
        if kml_dc:
            upload_kml_to_drive(kml_dc, base_cluster_name + ".kml", [GDRIVE_FOLDERS["DISTRIBUTION CABLE"]])
        else:
            st.error("❌ Tidak ditemukan file .kml dalam folder DISTRIBUTION CABLE.")

        kml_bc = extract_and_merge_kmls_from_kmz(uploaded_cluster, "BOUNDARY CLUSTER", base_cluster_name + "_BC.kml")
        if kml_bc:
            upload_kml_to_drive(kml_bc, base_cluster_name + ".kml", [GDRIVE_FOLDERS["BOUNDARY CLUSTER"]])
        else:
            st.error("❌ Tidak ditemukan file .kml dalam folder BOUNDARY CLUSTER.")

    if uploaded_subfeeder:
        kml_cable = extract_and_merge_kmls_from_kmz(uploaded_subfeeder, "CABLE", base_subfeeder_name + "_CABLE.kml")
        if kml_cable:
            upload_kml_to_drive(kml_cable, base_subfeeder_name + ".kml", [GDRIVE_FOLDERS["CABLE"]])
        else:
            st.error("❌ Tidak ditemukan file .kml dalam folder CABLE.")
