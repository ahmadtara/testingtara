import streamlit as st
import zipfile
import os
import tempfile
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
    """
    Ekstrak semua file .kml dalam folder target dari KMZ,
    gabungkan semua Placemark, dan simpan ke satu file .kml.
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        kmz_path = os.path.join(tmpdirname, kmz_file.name)
        with open(kmz_path, "wb") as f:
            f.write(kmz_file.read())

        try:
            with zipfile.ZipFile(kmz_path, 'r') as z:
                z.extractall(tmpdirname)
        except zipfile.BadZipFile:
            st.error("❌ File KMZ bukan file zip yang valid.")
            return None

        all_placemarks = []
        namespace = {"kml": "http://www.opengis.net/kml/2.2"}

        # Cari semua file .kml di folder target
        for root, dirs, files in os.walk(tmpdirname):
            if target_folder_name.lower() in root.lower():
                for file in files:
                    if file.endswith(".kml"):
                        kml_path = os.path.join(root, file)
                        try:
                            tree = ET.parse(kml_path)
                            root_elem = tree.getroot()
                            for placemark in root_elem.findall(".//kml:Placemark", namespace):
                                all_placemarks.append(placemark)
                        except ET.ParseError:
                            st.warning(f"⚠ Gagal parsing XML: {file}")

        if not all_placemarks:
            return None

        # Buat KML gabungan
        kml_root = ET.Element("{http://www.opengis.net/kml/2.2}kml")
        doc_elem = ET.SubElement(kml_root, "Document")
        ET.SubElement(doc_elem, "name").text = output_name

        for pm in all_placemarks:
            doc_elem.append(pm)

        combined_path = os.path.join(tempfile.gettempdir(), output_name)
        ET.ElementTree(kml_root).write(combined_path, encoding="utf-8", xml_declaration=True)

        return combined_path

def upload_kml_to_drive(kml_path, filename, folder_id):
    if not os.path.exists(kml_path):
        st.error(f"❌ File tidak ditemukan: {kml_path}")
        return

    try:
        service = get_drive_service()
        if not service:
            st.error("❌ Gagal mendapatkan layanan Google Drive.")
            return

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

uploaded_cluster = st.file_uploader("📄 Upload file .KMZ CLUSTER (berisi folder DISTRIBUTION CABLE & BOUNDARY CLUSTER)", type=["kmz"], key="cluster")
uploaded_subfeeder = st.file_uploader("📄 Upload file .KMZ SUBFEEDER (berisi folder CABLE)", type=["kmz"], key="subfeeder")
submit_clicked = st.button("🚀 Upload ke Google Drive")

if submit_clicked:
    base_cluster_name = uploaded_cluster.name.replace(".kmz", "") if uploaded_cluster else None
    base_subfeeder_name = uploaded_subfeeder.name.replace(".kmz", "") if uploaded_subfeeder else None

    # Proses CLUSTER
    if uploaded_cluster:
        for folder_name in ["DISTRIBUTION CABLE", "BOUNDARY CLUSTER"]:
            output_filename = f"{base_cluster_name}_{folder_name.replace(' ', '_')}.kml"
            kml_path = extract_and_merge_kmls_from_kmz(uploaded_cluster, folder_name, output_filename)
            if kml_path:
                upload_kml_to_drive(kml_path, output_filename, GDRIVE_FOLDERS[folder_name])
            else:
                st.error(f"❌ Tidak ditemukan file .kml dalam folder {folder_name}.")

    # Proses SUBFEEDER
    if uploaded_subfeeder:
        folder_name = "CABLE"
        output_filename = f"{base_subfeeder_name}_{folder_name}.kml"
        kml_path = extract_and_merge_kmls_from_kmz(uploaded_subfeeder, folder_name, output_filename)
        if kml_path:
            upload_kml_to_drive(kml_path, output_filename, GDRIVE_FOLDERS[folder_name])
        else:
            st.error(f"❌ Tidak ditemukan file .kml dalam folder {folder_name}.")
