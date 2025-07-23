import os
import geopandas as gpd
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import unary_union
import ezdxf
import streamlit as st
import tempfile
import json

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S (Indonesia Barat)

# --- Ekstrak Polygon Area dari KML ---
def extract_polygon_from_kml(kml_path):
    gdf = gpd.read_file(kml_path)
    polygons = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if polygons.empty:
        raise Exception("❌ Tidak ditemukan geometri Polygon dalam file KML.")
    return unary_union(polygons.geometry), polygons.crs

# --- Ambil Bangunan dari File GeoJSONL Lokal ---
def load_buildings_from_local_csv(polygon, local_path):
    st.info("📦 Mengambil bangunan dari file lokal (GeoJSONL)...")
    geometries = []
    with open(local_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                geom = shape(obj["geometry"])
                if geom.is_valid and geom.within(polygon):
                    geometries.append(geom)
            except json.JSONDecodeError:
                continue

    if not geometries:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    return gpd.GeoDataFrame(geometry=gpd.GeoSeries(geometries), crs="EPSG:4326")

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
def process_kml_to_dxf(kml_path, output_dir, local_csv_path):
    os.makedirs(output_dir, exist_ok=True)
    polygon, _ = extract_polygon_from_kml(kml_path)
    gdf = load_buildings_from_local_csv(polygon, local_csv_path)

    if gdf.empty:
        raise Exception("Tidak ada bangunan ditemukan di dalam area yang dipilih.")

    dxf_path = os.path.join(output_dir, "buildings_detected.dxf")
    export_to_dxf_buildings(gdf.to_crs(TARGET_EPSG), dxf_path)
    return dxf_path, True

# --- Streamlit UI ---
st.set_page_config(page_title="KML → DXF Auto Building Extractor", layout="wide")
st.title("🏠 KML → DXF Building Extractor")
st.caption("Upload file .KML (batas area perumahan) dan file GeoJSONL (.csv) hasil deteksi bangunan")

kml_file = st.file_uploader("📍 Upload file .KML", type=["kml"])
gbf_file = st.file_uploader("🏗️ Upload file GBF (GeoJSONL dalam .csv)", type=["csv", "jsonl"])

if kml_file and gbf_file:
    with st.spinner("💫 Memproses file dan mengekstrak bangunan..."):
        try:
            temp_kml = f"/tmp/{kml_file.name}"
            with open(temp_kml, "wb") as f:
                f.write(kml_file.read())

            temp_gbf = f"/tmp/{gbf_file.name}"
            with open(temp_gbf, "wb") as f:
                f.write(gbf_file.read())

            output_dir = "/tmp/output"
            dxf_path, ok = process_kml_to_dxf(temp_kml, output_dir, temp_gbf)

            if ok:
                st.success("✅ Berhasil diekspor ke DXF!")
                with open(dxf_path, "rb") as f:
                    st.download_button("⬇️ Download DXF", data=f, file_name="buildings_detected.dxf")
        except Exception as e:
            st.error(f"❌ Terjadi kesalahan: {e}")
