import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import geopandas as gpd
import streamlit as st
import ezdxf
import osmnx as ox
from fastkml import kml
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, MultiLineString
from shapely.ops import unary_union, linemerge, snap, polygonize, transform
from pyproj import Transformer

st.set_page_config(layout="wide")

# Constants
TARGET_EPSG = "EPSG:32760"
DEFAULT_WIDTH = 10

# Transformer for DXF output
utm_transformer = Transformer.from_crs("EPSG:4326", "EPSG:32760", always_xy=True)
# Transformer for OSM download (reverse)
osm_transformer = Transformer.from_crs("EPSG:32760", "EPSG:4326", always_xy=True)

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
                coords = []
                for c in line_coord.text.strip().split():
                    lon, lat, *_ = c.split(',')
                    coords.append((float(lat), float(lon)))
                items.append({
                    'type': 'path',
                    'name': name_text,
                    'coords': coords,
                    'folder': folder_name
                })
                continue

            poly_coord = pm.find('.//kml:Polygon//kml:coordinates', ns)
            if poly_coord is not None:
                coords = []
                for c in poly_coord.text.strip().split():
                    lon, lat, *_ = c.split(',')
                    coords.append((float(lat), float(lon)))
                items.append({
                    'type': 'polygon',
                    'name': name_text,
                    'coords': coords,
                    'folder': folder_name
                })
    return items

def classify_layer(name):
    if "HP COVER" in name:
        return "NN"
    elif "POLE" in name or "EXISTING" in name:
        return "MR"
    return None

def get_osm_streets_from_polygon(polygon_epsg_32760):
    # Convert polygon to EPSG:4326 for OSM download
    polygon_wgs84 = transform(lambda x, y: osm_transformer.transform(x, y), polygon_epsg_32760)
    try:
        gdf = ox.geometries_from_polygon(polygon_wgs84, tags={"highway": True})
        streets = gdf[gdf.geometry.type.isin(["LineString", "MultiLineString"])]
        return streets
    except Exception as e:
        st.warning(f"⚠️ Tidak ada jalan ditemukan di area tersebut.\n{e}")
        return gpd.GeoDataFrame()

def latlon_to_xy(lat, lon):
    return utm_transformer.transform(lon, lat)

def load_template_blocks(template_path):
    doc = ezdxf.readfile(template_path)
    return doc.modelspace(), doc

def main():
    st.title("Konversi KMZ ke DXF dengan Layering & OSM Road")
    uploaded = st.file_uploader("Unggah file KMZ", type=["kmz"])
    template = st.file_uploader("Template DXF (dengan block)", type=["dxf"])

    if uploaded and template:
        with tempfile.TemporaryDirectory() as tmpdir:
            kmz_path = os.path.join(tmpdir, uploaded.name)
            with open(kmz_path, "wb") as f:
                f.write(uploaded.getvalue())

            kml_path = extract_kmz(kmz_path, tmpdir)
            items = parse_kml(kml_path)
            polygons = [Polygon(i['coords']) for i in items if i['type'] == 'polygon' and i['folder'].startswith("BOUNDARY")]

            if not polygons:
                st.error("❌ Terjadi kesalahan: Tidak ada polygon dari folder 'BOUNDARY CLUSTER' ditemukan.")
                return

            boundary = unary_union(polygons)
            roads = get_osm_streets_from_polygon(boundary)

            msp, doc = load_template_blocks(template)
            
            for idx, item in enumerate(items):
                layer = classify_layer(item['folder'])
                if item['type'] == 'point':
                    x, y = latlon_to_xy(item['latitude'], item['longitude'])
                    msp.add_text(item['name'], dxfattribs={"layer": layer}).set_pos((x, y))
                elif item['type'] in ('path', 'polygon'):
                    coords = [latlon_to_xy(lat, lon) for lat, lon in item['coords']]
                    if item['type'] == 'path':
                        msp.add_lwpolyline(coords, dxfattribs={"layer": layer})
                    elif item['type'] == 'polygon':
                        msp.add_lwpolyline(coords, close=True, dxfattribs={"layer": layer})

            for _, row in roads.iterrows():
                geom = row.geometry
                if isinstance(geom, LineString):
                    coords = [utm_transformer.transform(*pt) for pt in geom.coords]
                    msp.add_lwpolyline(coords, dxfattribs={"layer": "ROAD"})
                elif isinstance(geom, MultiLineString):
                    for line in geom:
                        coords = [utm_transformer.transform(*pt) for pt in line.coords]
                        msp.add_lwpolyline(coords, dxfattribs={"layer": "ROAD"})

            output_path = os.path.join(tmpdir, "output.dxf")
            doc.saveas(output_path)
            with open(output_path, "rb") as f:
                st.download_button("Download DXF", f.read(), file_name="output.dxf")

if __name__ == "__main__":
    main()
