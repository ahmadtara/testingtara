import zipfile
from fastkml import kml
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- STEP 1: Baca file KMZ dan ekstrak folder NEW POLE 7-3 dan NEW POLE 7-4 ---
def extract_poles_from_kmz(kmz_path):
    with zipfile.ZipFile(kmz_path, 'r') as zf:
        with zf.open('doc.kml', 'r') as file:
            doc = file.read()

    k = kml.KML()
    k.from_string(doc)
    
    poles = []

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

# --- STEP 2: Tulis ke Google Spreadsheet ---
def append_to_google_sheet(data, spreadsheet_id, sheet_name, creds_json_path):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive']

    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_json_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)

    for item in data:
        row = [
            "", "", "", "", "",  # SubRegion, ProvinceName, City, District, SubDistrict
            item['Pole_Id'], item['PoleName'],
            item['Latitude'], item['Longitude'],
            "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""
        ]
        sheet.append_row(row)

# --- Contoh penggunaan ---
kmz_path = "namafile.kmz"
creds_json = "client_secret.json"
spreadsheet_id = "1yXBIuX2LjUWxbpnNqf6A9YimtG7d77V_AHLidhWKIS8"
sheet_name = "Pole Pekanbaru"  # atau sesuaikan dari tab aktif

pole_data = extract_poles_from_kmz(kmz_path)
append_to_google_sheet(pole_data, spreadsheet_id, sheet_name, creds_json)
