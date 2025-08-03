import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET
import streamlit as st
import ezdxf
import geopandas as gpd
from fastkml import kml
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, MultiLineString
from shapely.ops import unary_union, linemerge, snap, polygonize
import osmnx as ox
from pyproj import Transformer

TARGET_EPSG = "EPSG:32760"
DEFAULT_WIDTH = 10

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
        if folder_name != 'BOUNDARY CLUSTER':
            continue
        placemarks = folder.findall('.//kml:Placemark', ns)
        for pm in placemarks:
            name = pm.find('kml:name', ns)
            name_text = name.text.strip() if name is not None else ""

            polygon_coord = pm.find('.//kml:Polygon//kml:coordinates', ns)
            if polygon_coord is not None:
                coords = []
                for c in polygon_coord.text.strip().split():
                    lon, lat, *_ = c.split(',')
                    coords.append((float(lat), float(lon)))
                items.append({
                    'type': 'polygon',
                    'name': name_text,
                    'coords': coords,
                    'folder': folder_name
                })
    return items

def get_osm_streets_from_polygon(polygon, tags=None):
    if tags is None:
        tags = {"highway": True}
    try:
        gdf = ox.geometries_from_polygon(polygon, tags)
        if 'geometry' in gdf:
            return gdf[gdf.geometry.type.isin(['LineString', 'MultiLineString'])]
    except Exception as e:
        print("OSM Error:", e)
    return gpd.GeoDataFrame(columns=['geometry'])

def to_utm(lat, lon):
    transformer = Transformer.from_crs("EPSG:4326", TARGET_EPSG, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return x, y

def draw_streets_to_dxf(streets_gdf, dxf_path, layer_name="OSM_STREETS"):
    doc = ezdxf.new()
    msp = doc.modelspace()
    doc.layers.add(name=layer_name)

    for geom in streets_gdf.geometry:
        if isinstance(geom, LineString):
            points = [to_utm(lat, lon) for lon, lat in geom.coords]
            msp.add_lwpolyline(points, dxfattribs={"layer": layer_name})
        elif isinstance(geom, MultiLineString):
            for line in geom.geoms:
                points = [to_utm(lat, lon) for lon, lat in line.coords]
                msp.add_lwpolyline(points, dxfattribs={"layer": layer_name})

    doc.saveas(dxf_path)

def main():
    st.title("KMZ to DXF (OSM Jalan dari Folder 'BOUNDARY CLUSTER')")

    uploaded_file = st.file_uploader("Upload file KMZ", type="kmz")
    if uploaded_file is not None:
        with tempfile.TemporaryDirectory() as tmpdir:
            kmz_path = os.path.join(tmpdir, uploaded_file.name)
            with open(kmz_path, 'wb') as f:
                f.write(uploaded_file.read())

            kml_path = extract_kmz(kmz_path, tmpdir)
            items = parse_kml(kml_path)

            polygons = [Polygon(item['coords']) for item in items if item['type'] == 'polygon']

            if not polygons:
                st.error("❌ Terjadi kesalahan: Tidak ada polygon dari folder 'BOUNDARY CLUSTER' ditemukan.")
                return

            combined_polygon = unary_union(polygons)
            if isinstance(combined_polygon, (Polygon, MultiPolygon)):
                osm_streets = get_osm_streets_from_polygon(combined_polygon)

                if not osm_streets.empty:
                    dxf_output = os.path.join(tmpdir, "output_streets.dxf")
                    draw_streets_to_dxf(osm_streets, dxf_output)
                    st.success("✅ File DXF berhasil dibuat.")
                    with open(dxf_output, "rb") as f:
                        st.download_button("⬇️ Download DXF", f, file_name="OSM_Streets.dxf")
                else:
                    st.warning("⚠️ Tidak ada jalan ditemukan di area tersebut.")
            else:
                st.error("❌ Polygon gabungan tidak valid.")

if __name__ == "__main__":
    main()
