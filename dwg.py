import streamlit as st
import zipfile
from fastkml import kml
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tempfile

SPREADSHEET_ID = "1yXBIuX2LjUWxbpnNqf6A9YimtG7d77V_AHLidhWKIS8"
SHEET_NAME = "Pole Pekanbaru"

def authenticate_google():
    creds_dict = st.secrets["gcp_service_account"]
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(credentials)
    return client

def extract_poles_from_kmz(kmz_path):
    poles = []

    with zipfile.ZipFile(kmz_path, 'r') as zf:
        with zf.open('doc.kml', 'r') as file:
            doc = file.read()

    k = kml.KML()
    k.from_string(doc)

    for document in k.features():  # Level 1: <Document>
        for outer_folder in document.features():  # Level 2: LINE A, LINE B, LINE C
            for inner_folder in outer_folder.features():  # Level 3: NEW POLE 7-3/7-4
                if inner_folder.name in ['NEW POLE 7-3', 'NEW POLE 7-4']:
                    for placemark in inner_folder.features():
                        if placemark.geometry:
                            name = placemark.name
                            coord = list(placemark.geometry.coords)[0]
                            poles.append({
                                'Pole_Id': name,
                                'PoleName': name,
                                'Latitude': coord[1],
                                'Longitude': coord[0]
                            })
    return poles

def append_to_sheet(sheet, data):
    for item in data:
        row = [
            "", "", "", "", "", 
            item['Pole_Id'], item['PoleName'],
            item['Latitude'], item['Longitude']
        ] + [""] * 19
        sheet.append_row(row)

st.title("Uploader Pole KMZ ke Google Sheet")

uploaded_file = st.file_uploader("Upload file .kmz", type=["kmz"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kmz") as tmp:
        tmp.write(uploaded_file.read())
        kmz_path = tmp.name

    with st.spinner("Membaca dan memproses KMZ..."):
        poles = extract_poles_from_kmz(kmz_path)

    if poles:
        st.success(f"{len(poles)} titik ditemukan. Mengirim ke Google Sheets...")
        try:
            client = authenticate_google()
            sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
            append_to_sheet(sheet, poles)
            st.success("Data berhasil dikirim ke Google Sheet 🎉")
        except Exception as e:
            st.error(f"Gagal mengirim: {e}")
    else:
        st.warning("Tidak ada folder NEW POLE 7-3 atau 7-4 ditemukan dalam file KMZ.")
