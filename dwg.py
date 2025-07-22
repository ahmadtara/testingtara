import zipfile
import os
import math
import requests
import streamlit as st
from xml.etree import ElementTree as ET
import ezdxf
from tempfile import NamedTemporaryFile

HERE_API_KEY = "iWCrFicKYt9_AOCtg76h76MlqZkVTn94eHbBl_cE8m0"

def extract_kmz(kmz_path, extract_dir):
    with zipfile.ZipFile(kmz_path, 'r') as kmz_file:
        kmz_file.extractall(extract_dir)
    return os.path.join(extract_dir, "doc.kml")

def parse_kml(kml_path):
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    tree = ET.parse(kml_path)
    root = tree.getroot()
    placemarks = root.findall('.//kml:Placemark', ns)
    points = []
    for pm in placemarks:
        name = pm.find('kml:name', ns)
        coord = pm.find('.//kml:coordinates', ns)
        if name is not None and coord is not None:
            name_text = name.text.strip()
            coord_text = coord.text.strip()
            lon, lat, *_ = coord_text.split(',')
            points.append({
                'name': name_text,
                'latitude': float(lat),
                'longitude': float(lon)
            })
    return points

def parse_boundaries(kml_path):
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    tree = ET.parse(kml_path)
    root = tree.getroot()
    boundaries = []

    for folder in root.findall(".//kml:Folder", ns):
        name_tag = folder.find('kml:name', ns)
        if name_tag is not None and name_tag.text.strip().upper() == "BOUNDARY":
            placemarks = folder.findall(".//kml:Placemark", ns)
            for pm in placemarks:
                coords = pm.find('.//kml:coordinates', ns)
                if coords is not None:
                    coord_list = []
                    for pair in coords.text.strip().split():
                        lon, lat, *_ = map(float, pair.split(','))
                        coord_list.append(latlon_to_xy(lat, lon))
                    boundaries.append(coord_list)
    return boundaries

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def classify_points(points):
    classified = {"FDT": [], "FAT": [], "POLE": [], "EXISTING_POLE": [], "HP_COVER": [], "FAT_LAGI": []}
    for p in points:
        name = p['name'].upper()
        if "FDT" in name:
            classified["FDT"].append(p)
        elif "FAT" in name and "LAGI" in name:
            classified["FAT_LAGI"].append(p)
        elif "FAT" in name:
            classified["FAT"].append(p)
        elif "EXISTING" in name or "EMR" in name:
            classified["EXISTING_POLE"].append(p)
        elif "HP" in name or "HOME" in name or "COVER" in name:
            classified["HP_COVER"].append(p)
        elif "P" in name:
            classified["POLE"].append(p)
    return classified

def latlon_to_xy(lat, lon):
    return lon * 111320, lat * 110540

def find_nearest_pole(hp, poles):
    nearest = None
    min_dist = float('inf')
    for p in poles:
        d = haversine(hp['latitude'], hp['longitude'], p['latitude'], p['longitude'])
        if d < min_dist:
            min_dist = d
            nearest = p
    return nearest

def draw_boundaries(msp, boundaries):
    for polygon in boundaries:
        if polygon[0] != polygon[-1]:
            polygon.append(polygon[0])
        msp.add_lwpolyline(polygon, close=True, dxfattribs={"layer": "FAT AREA"})

def draw_dxf(classified, boundaries, output_path):
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()

    for p in classified["FDT"]:
        x, y = latlon_to_xy(p["latitude"], p["longitude"])
        size = 3
        msp.add_lwpolyline([(x, y), (x+size, y), (x+size, y+size), (x, y+size), (x, y)], close=True, dxfattribs={"layer": "FDT"})

    for p in classified["FAT"]:
        x, y = latlon_to_xy(p["latitude"], p["longitude"])
        size = 3
        msp.add_lwpolyline([(x, y), (x+size, y), (x+size, y+size), (x, y+size), (x, y)], close=True, dxfattribs={"layer": "FAT"})
        msp.add_text(p["name"], dxfattribs={"layer": "FAT"}).set_pos((x, y+size+1), align='LEFT')

    for p in classified["FAT_LAGI"]:
        x, y = latlon_to_xy(p["latitude"], p["longitude"])
        size = 3
        msp.add_lwpolyline([(x, y), (x+size, y), (x+size, y+size), (x, y+size), (x, y)], close=True, dxfattribs={"layer": "BA"})
        msp.add_text(p["name"], dxfattribs={"layer": "BA"}).set_pos((x, y+size+1), align='LEFT')

    for p in classified["POLE"]:
        x, y = latlon_to_xy(p["latitude"], p["longitude"])
        msp.add_text(p["name"], dxfattribs={"layer": "NP"}).set_pos((x, y), align='CENTER')

    for p in classified["EXISTING_POLE"]:
        x, y = latlon_to_xy(p["latitude"], p["longitude"])
        msp.add_circle((x, y), radius=2, dxfattribs={"layer": "LINGKAR MERAH"})

    for p in classified["HP_COVER"]:
        x, y = latlon_to_xy(p["latitude"], p["longitude"])
        msp.add_text(p["name"], dxfattribs={"layer": "LABEL_CABEL"}).set_pos((x, y), align='LEFT')

    draw_boundaries(msp, boundaries)
    doc.saveas(output_path)

def convert_kmz_to_dwg(kmz_file):
    extract_dir = "temp_kmz"
    os.makedirs(extract_dir, exist_ok=True)
    with NamedTemporaryFile(delete=False, suffix=".kmz") as tmp:
        tmp.write(kmz_file.read())
        tmp_path = tmp.name

    kml_path = extract_kmz(tmp_path, extract_dir)
    points = parse_kml(kml_path)
    classified = classify_points(points)
    boundaries = parse_boundaries(kml_path)

    output_path = tmp_path.replace(".kmz", ".dwg")
    draw_dxf(classified, boundaries, output_path)
    return output_path

def main():
    st.title("KMZ to DWG Converter (Fiber Legend)")
    st.write("Upload KMZ untuk dikonversi menjadi file DWG dengan layer sesuai legend.")

    uploaded_file = st.file_uploader("Upload KMZ file", type=["kmz"])

    if uploaded_file is not None:
        with st.spinner("Memproses file KMZ..."):
            dwg_path = convert_kmz_to_dwg(uploaded_file)
            st.success("Konversi selesai!")
            with open(dwg_path, "rb") as f:
                st.download_button("Download DWG", data=f, file_name="output.dwg")

if __name__ == "__main__":
    main()
