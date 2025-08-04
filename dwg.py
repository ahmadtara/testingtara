import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO

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
            if nm is not None and coord is not None:
                lon, lat = coord.text.strip().split(",")[:2]
                items.append({
                    "name": nm.text.strip(),
                    "lat": float(lat),
                    "lon": float(lon),
                    "path": new_path
                })
        return items

    with zipfile.ZipFile(kmz_path, 'r') as zf:
        kml_file = [f for f in zf.namelist() if f.lower().endswith(".kml")][0]
        root = ET.parse(zf.open(kml_file)).getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        all_pm = []
        for folder in root.findall(".//kml:Folder", ns):
            all_pm += recurse_folder(folder, ns)

    # filter hanya NEW POLE 7-3 dan 7-4
    for p in all_pm:
        if "NEW POLE 7-3" in p["path"] or "NEW POLE 7-4" in p["path"]:
            poles.append({
                "Pole_Id": p["name"],
                "PoleName": p["name"],
                "Latitude": p["lat"],
                "Longitude": p["lon"]
            })

    return poles
