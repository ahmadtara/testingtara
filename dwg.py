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

def extract_folder_as_kml(kmz_file, target_folder_name, output_name):
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

        doc_kml_path = os.path.join(tmpdirname, "doc.kml")
        if not os.path.exists(doc_kml_path):
            st.error("❌ Tidak ditemukan doc.kml di dalam KMZ.")
            return None

        # Parsing KML
        tree = ET.parse(doc_kml_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}

        # Cari folder target
        target_folders = []
        for folder in root.findall(".//kml:Folder", ns):
            name_tag = folder.find("kml:name", ns)
            if name_tag is not None and name_tag.text and target_folder_name.lower() in name_tag.text.lower():
                target_folders.append(folder)

        if not target_folders:
            return None

        # Buat KML baru dengan struktur asli, tapi hanya folder target
        new_kml = ET.Element(root.tag, root.attrib)
        for child in root:
            if child.tag.endswith("Document"):
                new_doc = ET.SubElement(new_kml, child.tag, child.attrib)
                # Copy style & schema dari doc asli
                for doc_child in child:
                    if not doc_child.tag.endswith("Folder"):
                        new_doc.append(doc_child)
                # Masukkan folder target
                for folder in target_folders:
                    new_doc.append(folder)

        # Simpan ke file
        combined_path = os.path.join(tempfile.gettempdir(), output_name)
        ET.ElementTree(new_kml).write(combined_path, encoding="utf-8", xml_declaration=True)
        return combined_path

def extract_folder_with_style(kmz_file, target_folder_name, output_name):
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Simpan file kmz ke temp
        kmz_path = os.path.join(tmpdirname, "temp.kmz")
        with open(kmz_path, "wb") as f:
            f.write(kmz_file.read())

        # Ekstrak isi kmz
        with zipfile.ZipFile(kmz_path, 'r') as z:
            z.extractall(tmpdirname)

        # Cari doc.kml
        doc_kml_path = None
        for root, dirs, files in os.walk(tmpdirname):
            for file in files:
                if file.lower() == "doc.kml":
                    doc_kml_path = os.path.join(root, file)
                    break

        if not doc_kml_path:
            print("❌ doc.kml tidak ditemukan.")
            return None

        # Parse doc.kml
        tree = ET.parse(doc_kml_path)
        root = tree.getroot()

        # Namespace (biar tag bisa terbaca dengan benar)
        ns = {"kml": "http://www.opengis.net/kml/2.2"}

        # Cari folder sesuai nama
        target_folders = []
        for folder in root.findall(".//kml:Folder", ns):
            name_tag = folder.find("kml:name", ns)
            if name_tag is not None and name_tag.text.strip().lower() == target_folder_name.lower():
                target_folders.append(folder)

        if not target_folders:
            print(f"❌ Folder '{target_folder_name}' tidak ditemukan.")
            return None

        # Buat dokumen baru dengan style asli
        new_root = ET.Element(root.tag, root.attrib)  # root <kml>
        for child in root:
            # Simpan semua style, schema, dll
            if child.tag.endswith("Document"):
                new_doc = ET.Element(child.tag, child.attrib)
                # Salin semua style
                for sub in child:
                    if sub.tag.endswith("Style") or sub.tag.endswith("StyleMap") or sub.tag.endswith("Schema"):
                        new_doc.append(sub)
                # Masukkan folder target
                for f in target_folders:
                    new_doc.append(f)
                new_root.append(new_doc)
            else:
                new_root.append(child)

        # Simpan hasil
        output_path = os.path.join(tempfile.gettempdir(), output_name)
        ET.ElementTree(new_root).write(output_path, encoding="utf-8", xml_declaration=True)
        print(f"✅ Disimpan: {output_path}")
        return output_path

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

uploaded_cluster = st.file_uploader("📄 Upload file .KMZ CLUSTER (berisi folder DISTRIBUTION CABLE & BOUNDARY CLUSTER)", type=["kmz"], key="cluster")
uploaded_subfeeder = st.file_uploader("📄 Upload file .KMZ SUBFEEDER (berisi folder CABLE)", type=["kmz"], key="subfeeder")
submit_clicked = st.button("🚀 Upload ke Google Drive")

if submit_clicked:
    base_cluster_name = uploaded_cluster.name.replace(".kmz", "") if uploaded_cluster else None
    base_subfeeder_name = uploaded_subfeeder.name.replace(".kmz", "") if uploaded_subfeeder else None

    if uploaded_cluster:
        for folder_name in ["DISTRIBUTION CABLE", "BOUNDARY CLUSTER"]:
            kml_path = extract_folder_as_kml(uploaded_cluster, folder_name, f"{base_cluster_name}_{folder_name.replace(' ', '_')}.kml")
            if kml_path:
                upload_kml_to_drive(kml_path, f"{base_cluster_name}_{folder_name.replace(' ', '_')}.kml", [GDRIVE_FOLDERS[folder_name]])
            else:
                st.error(f"❌ Tidak ditemukan folder {folder_name} di dalam KMZ.")

    if uploaded_subfeeder:
        kml_cable = extract_folder_as_kml(uploaded_subfeeder, "CABLE", f"{base_subfeeder_name}_CABLE.kml")
        if kml_cable:
            upload_kml_to_drive(kml_cable, f"{base_subfeeder_name}_CABLE.kml", [GDRIVE_FOLDERS["CABLE"]])
        else:
            st.error("❌ Tidak ditemukan folder CABLE di dalam KMZ.")

