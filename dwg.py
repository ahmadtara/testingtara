import os
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.ops import unary_union
import ezdxf
import streamlit as st
import tempfile
import pandas as pd
import json
import requests
from io import BytesIO
import gzip

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S

# --- Daftar URL GBF Tetap ---
GBF_URLS = [
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223031/part-00029-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223032/part-00066-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223033/part-00039-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223120/part-00068-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223122/part-00118-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223123/part-00012-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223020/part-00154-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223021/part-00101-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223022/part-00009-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223023/part-00155-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223030/part-00107-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223200/part-00188-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223201/part-00166-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223121/part-00176-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223213/part-00024-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223233/part-00070-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223132/part-00146-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223300/part-00005-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223302/part-00040-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223331/part-00034-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz",
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/2025-02-25/global-buildings.geojsonl/RegionName=Indonesia/quadkey=132223330/part-00173-5cf70943-9c5f-4fc6-94fb-43ce5feefa56.c000.csv.gz"
]

# --- Ekstrak Polygon Area dari KML ---
def extract_polygon_from_kml(kml_path):
    gdf = gpd.read_file(kml_path)
    polygons = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if polygons.empty:
        raise Exception("No Polygon found in KML")
    return unary_union(polygons.geometry), polygons.crs

# --- Ambil Bangunan dari Banyak URL GBF (GeoJSONL Format) ---
def load_buildings_from_gbf_multi(polygon, gbf_urls):
    st.info("📦 Mengambil bangunan dari beberapa file GBF (GeoJSONL)...")
    geometries = []
    for url in gbf_urls:
        try:
            r = requests.get(url)
            r.raise_for_status()
            with gzip.open(BytesIO(r.content), mode='rt') as f:
                for line in f:
                    if line:
                        obj = json.loads(line)
                        geom = shape(obj["geometry"])
                        if geom.is_valid and geom.within(polygon):
                            geometries.append(geom)
        except Exception as e:
            st.warning(f"⚠️ Gagal membaca: {url}\n{e}")

    if not geometries:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(geometries), crs="EPSG:4326")
    return gdf

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
def process_kml_to_dxf(kml_path, output_dir, gbf_urls):
    os.makedirs(output_dir, exist_ok=True)
    polygon, _ = extract_polygon_from_kml(kml_path)

    gdf = load_buildings_from_gbf_multi(polygon, gbf_urls)
    if gdf.empty:
        raise Exception("Tidak ada bangunan dalam area ini.")

    dxf_path = os.path.join(output_dir, "buildings_detected.dxf")
    export_to_dxf_buildings(gdf.to_crs(TARGET_EPSG), dxf_path)
    return dxf_path, True

# --- Streamlit UI ---
st.set_page_config(page_title="KML → DXF Auto Building Extractor", layout="wide")
st.title("🏠 KML → DXF Building Extractor (GBF Multiple)")
st.caption("Upload file .KML (batas area perumahan)")

kml_file = st.file_uploader("Upload file .KML", type=["kml"])

if kml_file:
    with st.spinner("💫 Memproses file dan mengekstrak bangunan..."):
        try:
            temp_input = f"/tmp/{kml_file.name}"
            with open(temp_input, "wb") as f:
                f.write(kml_file.read())

            output_dir = "/tmp/output"
            dxf_path, ok = process_kml_to_dxf(temp_input, output_dir, GBF_URLS)

            if ok:
                st.success("✅ Berhasil diekspor ke DXF!")
                with open(dxf_path, "rb") as f:
                    st.download_button("⬇️ Download DXF", data=f, file_name="buildings_detected.dxf")
        except Exception as e:
            st.error(f"❌ Terjadi kesalahan: {e}")
