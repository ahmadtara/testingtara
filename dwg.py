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
                "Height": "7" if "7-3" in p["path"] or "7-4" in p["path"] else "9"
            })

    return poles

def append_to_sheet(sheet, data, district, subdistrict, vendor):
    values = sheet.get_all_values()
    last_row = max(len(col) for col in values)
    prev_row = sheet.row_values(last_row)

    today = datetime.today()
    formatted_date = today.strftime("%d/%m/%Y") if prev_row[33].count("/") == 2 else today.strftime("%Y-%m-%d")

    count_types = {"7m3inch": 0, "7m4inch": 0, "9m4inch": 0}

    district = district.upper()
    subdistrict = subdistrict.upper()
    vendor = vendor.upper()

    all_rows = []
    for pole in data:
        count_types[pole['Folder']] += 1

        row = [""] * 44
        row[0] = prev_row[0].upper()  # A Region
        row[1] = prev_row[1].upper()  # B SubRegion
        row[2] = prev_row[2].upper()  # C ProvinceName
        row[3] = prev_row[3].upper()  # D City
        row[4] = district              # E District
        row[5] = subdistrict           # F Subdistrict
        row[6] = pole['Pole_Id']       # G Pole_Id
        row[7] = pole['PoleName']      # H PoleName
        row[8] = pole['Latitude']      # I Latitude
        row[9] = pole['Longitude']     # J Longitude
        row[13] = prev_row[13]         # N ConstructionStage
        row[14] = prev_row[14]         # O accessibility
        row[15] = prev_row[15]         # P ActivationStage
        row[16] = prev_row[16]         # Q HierarchyType
        row[17] = pole['Folder']       # R PoleType
        row[25] = pole['Height']       # Z Pole Height
        row[27] = vendor               # AB VendorName
        row[29] = prev_row[30]         # AD InstallationYear
        row[30] = prev_row[31]         # AE ProductionYear
        row[33] = formatted_date       # AH InstallationDate
        row[42] = "Cluster"            # AQ Remarks

        all_rows.append(row)

    sheet.append_rows(all_rows)

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
    vendor_input = st.text_input("Vendor Name (AC)")

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
