import streamlit as st
import zipfile
from fastkml import kml
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tempfile

# SETUP GOOGLE SHEET
SPREADSHEET_ID = "1yXBIuX2LjUWxbpnNqf6A9YimtG7d77V_AHLidhWKIS8"
SHEET_NAME = "Pole Pekanbaru"

def authenticate_google():
    # Kalau pakai .streamlit/secrets.toml
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
    
    for d in k.features():
        for folder in d.features():
            if folder.name in ['NEW POLE 7-3', 'NEW POLE 7-4']:
                for placemark in folder.features():
                    name = placemark.name
                    coord = list(placemark.geometry.coords)[0]  # (lon, lat)
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
            "", "", "", "", "",                  # Subregion, ProvinceName, City, District, SubDistrict
            item['Pole_Id'], item['PoleName'],
            item['Latitude'], item['Longitude']
        ] + [""] * 19  # Sisanya biar sesuai kolom
        sheet.append_row(row)

# UI
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
