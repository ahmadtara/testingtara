import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tempfile
import datetime

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
        if "NEW POLE 7-3" in p["path"] or "NEW POLE 7-4" in p["path"]:
            poles.append({
                "Pole_Id": p["name"],
                "PoleName": p["name"],
                "Latitude": p["lat"],
                "Longitude": p["lon"],
                "folder": p["path"]
            })

    return poles

def append_to_sheet(sheet, poles, dupe_values, manual_values):
    today_fmt = sheet.cell(2, 34).value  # AH column = col 34
    today = datetime.datetime.today()

    for item in poles:
        folder = item.get("folder", "")
        if "7-4" in folder:
            pole_type = "7m4inch"
            pole_height = "7"
        elif "7-3" in folder:
            pole_type = "7m3inch"
            pole_height = "7"
        else:
            pole_type = "UNKNOWN"
            pole_height = ""

        row = [
            dupe_values.get("Region", ""),
            dupe_values.get("SubRegion", ""),
            dupe_values.get("ProvinceName", ""),
            dupe_values.get("City", ""),
            manual_values.get("District", ""),
            manual_values.get("Subdistrict", ""),
            item["Pole_Id"],
            item["PoleName"],
            item["Latitude"],
            item["Longitude"],
        ] + [""] * 4 + [
            dupe_values.get("ConstructionStage", ""),
            dupe_values.get("Accessibility", ""),
            dupe_values.get("ActivationStage", ""),
            dupe_values.get("HierarchyType", "")
        ] + [""] * 7 + [
            pole_type
        ] + [""] * 9 + [
            pole_height
        ] + [""] * 3 + [
            dupe_values.get("InstallationYear", ""),
            dupe_values.get("ProductionYear", ""),
            today.strftime(today_fmt),
        ] + [""] * 8 + [
            manual_values.get("VendorName", ""),
            "Cluster"
        ]

        sheet.append_row(row)

st.set_page_config(page_title="Upload Pole KMZ ke Google Sheet", layout="centered")
st.title("📡 Uploader Pole KMZ ke Google Sheet")

# Input manual
st.subheader("📝 Keterangan Manual")
district = st.text_input("District (Kolom E)")
subdistrict = st.text_input("Subdistrict (Kolom F)")
vendor = st.text_input("Vendor Name (Kolom AB)")

uploaded_file = st.file_uploader("📤 Upload file .KMZ", type=["kmz"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kmz") as tmp:
        tmp.write(uploaded_file.read())
        kmz_path = tmp.name

    with st.spinner("🔍 Membaca dan memproses KMZ..."):
        poles = extract_poles_from_kmz(kmz_path)

    if poles:
        try:
            client = authenticate_google()
            sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
            header = sheet.row_values(2)

            dupe_values = {
                "Region": header[0],
                "SubRegion": header[1],
                "ProvinceName": header[2],
                "City": header[3],
                "ConstructionStage": header[13],
                "Accessibility": header[14],
                "ActivationStage": header[15],
                "HierarchyType": header[16],
                "InstallationYear": header[29],
                "ProductionYear": header[30],
            }

            manual_values = {
                "District": district,
                "Subdistrict": subdistrict,
                "VendorName": vendor
            }

            append_to_sheet(sheet, poles, dupe_values, manual_values)
            st.success(f"✅ {len(poles)} titik berhasil dikirim ke Google Sheet 🎉")

        except Exception as e:
            st.error(f"❌ Gagal mengirim: {e}")
    else:
        st.warning("⚠️ Tidak ada folder NEW POLE 7-3 atau 7-4 ditemukan dalam file KMZ.")
