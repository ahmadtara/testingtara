import os
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import ezdxf
import streamlit as st
import tempfile
import osmnx as ox

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S

# --- Ekstrak Polygon Area dari KML ---
def extract_polygon_from_kml(kml_path):
    gdf = gpd.read_file(kml_path)
    polygons = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if polygons.empty:
        raise Exception("No Polygon found in KML")
    return unary_union(polygons.geometry), polygons.crs

# --- Ambil Bangunan dari OSM via Overpass ---
def load_buildings_from_osm(polygon):
    st.info("📦 Mengambil bangunan dari OSM via Overpass...")
    try:
        gdf = ox.geometries_from_polygon(polygon, tags={"building": True})
        gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
        return gdf
    except Exception as e:
        raise Exception(f"Gagal mengambil bangunan dari OSM: {e}")

# --- Ekspor ke DXF ---
def export_to_dxf_buildings(gdf, dxf_path):
    doc = ezdxf.new()
    msp = doc.modelspace()

    bounds = [(pt[0], pt[1]) for geom in gdf.geometry for pt in geom.exterior.coords]
    min_x = min(x for x, y in bounds)
    min_y = min(y for x, y in bounds)

    for geom in gdf.geometry:
        if geom.geom_type == "Polygon":
            coords = [(pt[0] - min_x, pt[1] - min_y) for pt in geom.exterior.coords]
            msp.add_lwpolyline(coords, dxfattribs={"layer": "BUILDINGS"})
        elif geom.geom_type == "MultiPolygon":
            for poly in geom.geoms:
                coords = [(pt[0] - min_x, pt[1] - min_y) for pt in poly.exterior.coords]
                msp.add_lwpolyline(coords, dxfattribs={"layer": "BUILDINGS"})

    doc.set_modelspace_vport(height=10000)
    doc.saveas(dxf_path)

# --- Proses Utama ---
def process_kml_to_dxf(kml_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    polygon, _ = extract_polygon_from_kml(kml_path)

    gdf = load_buildings_from_osm(polygon)
    if gdf.empty:
        raise Exception("Tidak ada bangunan dalam area ini.")

    dxf_path = os.path.join(output_dir, "buildings_detected.dxf")
    export_to_dxf_buildings(gdf.to_crs(TARGET_EPSG), dxf_path)
    return dxf_path, True

# --- Streamlit UI ---
st.set_page_config(page_title="KML → DXF Auto Building Extractor", layout="wide")
st.title("🏠 KML → DXF Building Extractor (OSM Overpass)")
st.caption("Upload file .KML (batas area perumahan)")

kml_file = st.file_uploader("Upload file .KML", type=["kml"])

if kml_file:
    with st.spinner("💫 Memproses file dan mengekstrak bangunan..."):
        try:
            temp_input = f"/tmp/{kml_file.name}"
            with open(temp_input, "wb") as f:
                f.write(kml_file.read())

            output_dir = "/tmp/output"
            dxf_path, ok = process_kml_to_dxf(temp_input, output_dir)

            if ok:
                st.success("✅ Berhasil diekspor ke DXF!")
                with open(dxf_path, "rb") as f:
                    st.download_button("⬇️ Download DXF", data=f, file_name="buildings_detected.dxf")
        except Exception as e:
            st.error(f"❌ Terjadi kesalahan: {e}")
