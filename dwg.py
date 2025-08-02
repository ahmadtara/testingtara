import streamlit as st
import zipfile
import os
from xml.etree import ElementTree as ET
import ezdxf
from pyproj import Transformer

st.set_page_config(page_title="KMZ → DXF ke Template", layout="wide")

transformer = Transformer.from_crs("EPSG:4326", "EPSG:32760", always_xy=True)

target_folders = {
    'FDT', 'FAT', 'HP COVER', 'NEW POLE 7-3', 'NEW POLE 7-4',
    'EXISTING POLE EMR 7-4', 'EXISTING POLE EMR 7-3',
    'BOUNDARY', 'DISTRIBUTION CABLE', 'SLING WIRE'
}

def extract_kmz(kmz_path, extract_dir):
    with zipfile.ZipFile(kmz_path, 'r') as kmz_file:
        kmz_file.extractall(extract_dir)
    return os.path.join(extract_dir, "doc.kml")

def parse_kml(kml_path):
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    with open(kml_path, 'rb') as f:
        tree = ET.parse(f)
    root = tree.getroot()
    folders = root.findall('.//kml:Folder', ns)
    items = []
    for folder in folders:
        folder_name_tag = folder.find('kml:name', ns)
        if folder_name_tag is None:
            continue
        folder_name = folder_name_tag.text.strip().upper()
        if folder_name not in target_folders:
            continue
        placemarks = folder.findall('.//kml:Placemark', ns)
        for pm in placemarks:
            name = pm.find('kml:name', ns)
            name_text = name.text.strip() if name is not None else ""

            point_coord = pm.find('.//kml:Point/kml:coordinates', ns)
            if point_coord is not None:
                lon, lat, *_ = point_coord.text.strip().split(',')
                items.append({
                    'type': 'point',
                    'name': name_text,
                    'latitude': float(lat),
                    'longitude': float(lon),
                    'folder': folder_name
                })
                continue

            line_coord = pm.find('.//kml:LineString/kml:coordinates', ns)
            if line_coord is not None:
                coords = [(float(lat), float(lon)) for lon, lat, *_ in [c.split(',') for c in line_coord.text.strip().split()]]
                items.append({
                    'type': 'path',
                    'name': name_text,
                    'coords': coords,
                    'folder': folder_name
                })
                continue

            poly_coord = pm.find('.//kml:Polygon//kml:coordinates', ns)
            if poly_coord is not None:
                coords = [(float(lat), float(lon)) for lon, lat, *_ in [c.split(',') for c in poly_coord.text.strip().split()]]
                items.append({
                    'type': 'path',
                    'name': name_text,
                    'coords': coords,
                    'folder': folder_name
                })
    return items

def latlon_to_xy(lat, lon):
    return transformer.transform(lon, lat)

def apply_offset(points_xy):
    xs = [x for x, y in points_xy]
    ys = [y for x, y in points_xy]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    return [(x - cx, y - cy) for x, y in points_xy], (cx, cy)

def classify_items(items):
    classified = {name: [] for name in [
        "FDT", "FAT", "HP_COVER", "NEW_POLE", "EXISTING_POLE", "POLE",
        "BOUNDARY", "DISTRIBUTION_CABLE", "SLING_WIRE"]}
    for it in items:
        folder = it['folder']
        if "FDT" in folder:
            classified["FDT"].append(it)
        elif "FAT" in folder and folder != "FAT AREA":
            classified["FAT"].append(it)
        elif "HP COVER" in folder:
            classified["HP_COVER"].append(it)
        elif "NEW POLE" in folder:
            classified["NEW_POLE"].append(it)
        elif "EXISTING" in folder or "EMR" in folder:
            classified["EXISTING_POLE"].append(it)
        elif "BOUNDARY" in folder:
            classified["BOUNDARY"].append(it)
        elif "DISTRIBUTION CABLE" in folder:
            classified["DISTRIBUTION_CABLE"].append(it)
        elif "SLING WIRE" in folder:
            classified["SLING_WIRE"].append(it)
        else:
            classified["POLE"].append(it)
    return classified

def draw_to_template(classified, template_path):
    doc = ezdxf.readfile(template_path)
    msp = doc.modelspace()

    matchprop_hp = matchprop_pole = matchprop_sr = None
    for e in msp.query('TEXT'):
        txt = e.dxf.text.upper()
        if 'NN-' in txt:
            matchprop_hp = e.dxf
        elif 'MR.SRMRW16' in txt:
            matchprop_pole = e.dxf
        elif 'SRMRW16.067.B01' in txt:
            matchprop_sr = e.dxf

    block_names = {b.name.upper(): b for b in doc.blocks}

    all_xy = []
    for cat_items in classified.values():
        for obj in cat_items:
            if obj['type'] == 'point':
                all_xy.append(latlon_to_xy(obj['latitude'], obj['longitude']))
            elif obj['type'] == 'path':
                all_xy.extend([latlon_to_xy(lat, lon) for lat, lon in obj['coords']])

    if not all_xy:
        st.error("❌ Tidak ada data dari KMZ!")
        return None

    shifted_all, (cx, cy) = apply_offset(all_xy)

    idx = 0
    for cat_items in classified.values():
        for obj in cat_items:
            if obj['type'] == 'point':
                obj['xy'] = shifted_all[idx]
                idx += 1
            elif obj['type'] == 'path':
                obj['xy_path'] = shifted_all[idx: idx + len(obj['coords'])]
                idx += len(obj['coords'])

    for layer_name, cat_items in classified.items():
        for obj in cat_items:
            if obj['type'] != 'point':
                continue

            x, y = obj['xy']
            block_inserted = False
            name_upper = obj["name"].upper()

            if layer_name == "FDT" and "FDT" in block_names:
                msp.add_blockref("FDT", insert=(x, y), dxfattribs={"layer": layer_name, "xscale": 0.005, "yscale": 0.005})
                block_inserted = True
            elif layer_name == "FAT" and "FAT" in block_names:
                msp.add_blockref("FAT", insert=(x, y), dxfattribs={"layer": layer_name})
                block_inserted = True
            elif layer_name in ["NEW_POLE", "EXISTING_POLE"] and "A$C14DD5346" in block_names:
                msp.add_blockref("A$C14DD5346", insert=(x, y), dxfattribs={"layer": layer_name})
                block_inserted = True

            if not block_inserted and layer_name != "HP_COVER":
                msp.add_circle(center=(x, y), radius=2, dxfattribs={"layer": layer_name})

            # Tambahkan teks agar tidak tumpang tindih
            if not block_inserted or layer_name not in ["FDT"]:
                height = getattr(matchprop_sr if layer_name in ["FAT", "FDT"] else matchprop_pole, "height", 1.5)
                color = getattr(matchprop_sr if layer_name in ["FAT", "FDT"] else matchprop_pole, "color", 256)
                msp.add_text(obj["name"], dxfattribs={
                    "height": height,
                    "layer": layer_name,
                    "color": color,
                    "insert": (x, y + 3.5)
                })

            elif block_inserted and layer_name == "FDT":
                continue

            if obj['type'] == 'path':
                msp.add_lwpolyline(obj['xy_path'], dxfattribs={"layer": layer_name})

    return doc

st.title("🏗️ KMZ → DXF (Masuk ke Template)")

uploaded_kmz = st.file_uploader("📂 Upload File KMZ", type=["kmz"])
uploaded_template = st.file_uploader("📐 Upload Template DXF", type=["dxf"])

if uploaded_kmz and uploaded_template:
    extract_dir = "temp_kmz"
    os.makedirs(extract_dir, exist_ok=True)
    output_dxf = "converted_output.dxf"

    with open("template_ref.dxf", "wb") as f:
        f.write(uploaded_template.read())

    with st.spinner("🔍 Memproses data..."):
        kml_path = extract_kmz(uploaded_kmz, extract_dir)
        items = parse_kml(kml_path)
        classified = classify_items(items)
        updated_doc = draw_to_template(classified, "template_ref.dxf")
        if updated_doc:
            updated_doc.saveas(output_dxf)

    if os.path.exists(output_dxf):
        st.success("✅ Konversi berhasil! DXF sudah dibuat berdasarkan template.")
        with open(output_dxf, "rb") as f:
            st.download_button("⬇️ Download DXF", f, file_name="output_from_kmz.dxf")
