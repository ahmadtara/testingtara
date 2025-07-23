import os
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import ezdxf
import streamlit as st
import tempfile

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S

# --- Ekstrak Polygon Area dari KML ---
def extract_polygon_from_kml(kml_path):
    gdf = gpd.read_file(kml_path)
    polygons = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if polygons.empty:
        raise Exception("No Polygon found in KML")
    return unary_union(polygons.geometry), polygons.crs

# --- Ambil Bangunan dari GBF HuggingFace ---
def load_buildings_from_gbf(polygon, gbf_url):
    st.info("📦 Mengambil bangunan dari GBF via HuggingFace...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            local_file = os.path.join(tmpdir, "indonesia.geojson")
            gdf = gpd.read_file(gbf_url)
            gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
            gdf = gdf[gdf.geometry.within(polygon)]
            return gdf
    except Exception as e:
        raise Exception(f"Gagal membaca GBF dari HuggingFace: {e}")

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
def process_kml_to_dxf(kml_path, output_dir, gbf_url):
    os.makedirs(output_dir, exist_ok=True)
    polygon, _ = extract_polygon_from_kml(kml_path)

    gdf = load_buildings_from_gbf(polygon, gbf_url)
    if gdf.empty:
        raise Exception("Tidak ada bangunan dalam area ini.")

    dxf_path = os.path.join(output_dir, "buildings_detected.dxf")
    export_to_dxf_buildings(gdf.to_crs(TARGET_EPSG), dxf_path)
    return dxf_path, True

# --- Streamlit UI ---
st.set_page_config(page_title="KML → DXF Auto Building Extractor", layout="wide")
st.title("🏠 KML → DXF Building Extractor (GBF HuggingFace)")
st.caption("Upload file .KML (batas area perumahan)")

kml_file = st.file_uploader("Upload file .KML", type=["kml"])
gbf_url = st.text_input("Masukkan URL GeoJSON GBF dari HuggingFace:", placeholder="https://huggingface.co/.../file.geojson")

if kml_file and gbf_url:
    with st.spinner("💫 Memproses file dan mengekstrak bangunan..."):
        try:
            temp_input = f"/tmp/{kml_file.name}"
            with open(temp_input, "wb") as f:
                f.write(kml_file.read())

            output_dir = "/tmp/output"
            dxf_path, ok = process_kml_to_dxf(temp_input, output_dir, gbf_url)

            if ok:
                st.success("✅ Berhasil diekspor ke DXF!")
                with open(dxf_path, "rb") as f:
                    st.download_button("⬇️ Download DXF", data=f, file_name="buildings_detected.dxf")
        except Exception as e:
            st.error(f"❌ Terjadi kesalahan: {e}")
