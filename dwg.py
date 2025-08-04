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

_cached_headers = None
_cached_prev_row = None

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
        base_folder = p["path"].split("/")[0].upper()
        if base_folder in ["NEW POLE 7-3", "NEW POLE 7-4", "NEW POLE 9-4"]:
            poles.append({
                "Pole_Id": p["name"],
                "PoleName": p["name"],
                "lat": p["lat"],
                "lon": p["lon"],
                "Folder": "7m3inch" if "7-3" in base_folder else "9m4inch" if "9-4" in base_folder else "7m4inch",
                "Height": "7" if "7-3" in base_folder or "7-4" in base_folder else "9"
            })

    return poles

def append_to_sheet(sheet, data, district, subdistrict, vendor):
    global _cached_headers, _cached_prev_row

    headers = _cached_headers or sheet.row_values(1)
    _cached_headers = headers
    header_map = {name.strip().lower(): i for i, name in enumerate(headers)}

    values = sheet.get_all_values()
    cell_count = sum(len(row) for row in values)
    if cell_count + len(data) * len(headers) > 10_000_000:
        st.error("❌ Gagal mengirim: Melebihi batas 10.000.000 sel di Google Sheets")
        return

    for i in range(len(values)-1, 0, -1):
        if any(values[i]):
            prev_row = values[i]
            break
    else:
        prev_row = [""] * len(headers)

    _cached_prev_row = prev_row

    today = datetime.today()
    formatted_date = today.strftime("%d/%m/%Y") if prev_row[header_map.get('installationdate', 0)].count("/") == 2 else today.strftime("%Y-%m-%d")

    count_types = {"7m3inch": 0, "7m4inch": 0, "9m4inch": 0}

    district = district.upper()
    subdistrict = subdistrict.upper()
    vendor = vendor.upper()

    all_rows = []
    for pole in data:
        count_types[pole['Folder']] += 1

        row = [""] * len(headers)

        # Kolom A-J berdasarkan urutan
        row[0] = prev_row[0] if len(prev_row) > 0 else ""
        row[1] = prev_row[1] if len(prev_row) > 1 else ""
        row[2] = prev_row[2] if len(prev_row) > 2 else ""
        row[3] = prev_row[3] if len(prev_row) > 3 else ""
        row[4] = district
        row[5] = subdistrict
        row[6] = pole['Pole_Id']
        row[7] = pole['PoleName']
        row[8] = pole['lat']
        row[9] = pole['lon']

        # Kolom N-Q berdasarkan nama header
        if 'constructionstage' in header_map:
            row[header_map['constructionstage']] = prev_row[header_map['constructionstage']]
        if 'accessibility' in header_map:
            row[header_map['accessibility']] = prev_row[header_map['accessibility']]
        if 'activationstage' in header_map:
            row[header_map['activationstage']] = prev_row[header_map['activationstage']]
        if 'hierarchytype' in header_map:
            row[header_map['hierarchytype']] = prev_row[header_map['hierarchytype']]

        for col in ['pole height', 'vendorname', 'installationyear', 'productionyear', 'installationdate', 'remarks']:
            idx = header_map.get(col.lower())
            if idx is not None:
                if col.lower() == 'pole height':
                    row[idx] = pole['Height']
                elif col.lower() == 'vendorname':
                    row[idx] = vendor
                elif col.lower() in ['installationyear', 'productionyear']:
                    row[idx] = str(today.year)
                elif col.lower() == 'installationdate':
                    row[idx] = formatted_date
                elif col.lower() == 'remarks':
                    row[idx] = "CLUSTER"

        if 'poletype' in header_map:
            row[header_map['poletype']] = pole['Folder']

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
