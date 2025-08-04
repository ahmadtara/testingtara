import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tempfile
from datetime import datetime

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

    def recurse_folder(folder, ns, path=""):
        items = []
        name_el = folder.find("kml:name", ns)
        folder_name = name_el.text.upper() if name_el is not None else "UNKNOWN"
        new_path = f"{path}/{folder_name}" if path else folder_name
        for sub in folder.findall("kml:Folder", ns):
            items += recurse_folder(sub, ns, new_path)
        for pm in folder.findall("kml:Placemark", ns):
            nm = pm.find("kml:name", ns)
            coord = pm.find(".//kml:coordinates", ns)
            if nm is not None and coord is not None and ',' in coord.text:
                lon, lat = coord.text.strip().split(",")[:2]
                items.append({
                    "name": nm.text.strip(),
                    "lat": float(lat),
                    "lon": float(lon),
                    "path": new_path
                })
        return items

    with zipfile.ZipFile(kmz_path, 'r') as zf:
        kml_file = next((f for f in zf.namelist() if f.lower().endswith(".kml")), None)
        if not kml_file:
            st.error("❌ Tidak ditemukan file .kml dalam .kmz")
            return []

        root = ET.parse(zf.open(kml_file)).getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        all_pm = []
        for folder in root.findall(".//kml:Folder", ns):
            all_pm += recurse_folder(folder, ns)

    for p in all_pm:
        if "NEW POLE 7-3" in p["path"] or "NEW POLE 7-4" in p["path"] or "NEW POLE 9-4" in p["path"]:
            poles.append({
                "Pole_Id": p["name"],
                "PoleName": p["name"],
                "Latitude": p["lat"],
                "Longitude": p["lon"],
                "Folder": "7m3inch" if "7-3" in p["path"] else "9m4inch" if "9-4" in p["path"] else "7m4inch",
                "Height": "7" if "7-3" in p["path"] else "9" if "9-4" in p["path"] else "9"
            })

    return poles

def copy_case(reference: str, value: str):
    return value.upper() if reference.isupper() else value.lower() if reference.islower() else value

def append_to_sheet(sheet, data, district, subdistrict, vendor):
    values = sheet.get_all_values()
    last_row = max(len(col) for col in values)
    prev_row = sheet.row_values(last_row)

    today = datetime.today()
    formatted_date = today.strftime("%d/%m/%Y") if prev_row[33].count("/") == 2 else today.strftime("%Y-%m-%d")

    count_types = {"7m3inch": 0, "7m4inch": 0, "9m4inch": 0}

    for pole in data:
        count_types[pole['Folder']] += 1

        row = [
            copy_case(prev_row[0], prev_row[0]),  # A Region
            copy_case(prev_row[1], prev_row[1]),  # B SubRegion
            copy_case(prev_row[2], prev_row[2]),  # C ProvinceName
            copy_case(prev_row[3], prev_row[3]),  # D City
            district,                             # E
            subdistrict,                          # F
            pole['Pole_Id'],                      # G
            pole['PoleName'],                     # H
            pole['Latitude'],                     # I
            pole['Longitude'],                    # J
            "", "", "", "",                        # K - N kosong
            copy_case(prev_row[13], prev_row[13]),# N ConstructionStage
            copy_case(prev_row[14], prev_row[14]),# O accessibility
            copy_case(prev_row[15], prev_row[15]),# P ActivationStage
            copy_case(prev_row[16], prev_row[16]),# Q HierarchyType
            pole['Folder'],                       # R PoleType
            "", "", "", "", "", "", "", "",         # S - Y kosong
            pole['Height'],                       # Z Pole Height
            "", "",                                # AA - AC kosong
            copy_case(prev_row[30], prev_row[30]),# AD InstallationYear
            copy_case(prev_row[31], prev_row[31]),# AE ProductionYear
            vendor,                               # AF / AB VendorName
            formatted_date,                       # AG / AH InstallationDate
            "", "", "", "", "", "",                 # AI - AP kosong
            "Cluster",                            # AQ remark
            "", "", ""                             # AR - AT kosong
        ]
        sheet.append_row(row)

    st.info(f"""
📊 **Ringkasan Pengunggahan**:
- 7m3inch: {count_types['7m3inch']} titik
- 7m4inch: {count_types['7m4inch']} titik
- 9m4inch: {count_types['9m4inch']} titik
""")

st.set_page_config(page_title="Upload Pole", layout="centered")
st.title("📡 Uploader Pole KMZ ke Google Sheet")

col1, col2, col3 = st.columns(3)
with col1:
    district_input = st.text_input("District (E)")
with col2:
    subdistrict_input = st.text_input("Subdistrict (F)")
with col3:
    vendor_input = st.text_input("Vendor Name (AB)")

uploaded_file = st.file_uploader("📤 Upload file .KMZ", type=["kmz"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kmz") as tmp:
        tmp.write(uploaded_file.read())
        kmz_path = tmp.name

    with st.spinner("🔍 Membaca dan memproses KMZ..."):
        poles = extract_poles_from_kmz(kmz_path)

    if poles:
        st.success(f"✅ {len(poles)} titik ditemukan. Mengirim ke Google Sheets...")
        try:
            client = authenticate_google()
            sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
            append_to_sheet(sheet, poles, district_input, subdistrict_input, vendor_input)
            st.success("✅ Data berhasil dikirim ke Google Sheet 🎉")
        except Exception as e:
            st.error(f"❌ Gagal mengirim: {e}")
    else:
        st.warning("⚠️ Tidak ada folder NEW POLE 7-3, 7-4, atau 9-4 ditemukan dalam file KMZ.")
