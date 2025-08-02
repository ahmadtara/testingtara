import os
import zipfile
import tempfile
from io import BytesIO
import streamlit as st
import geopandas as gpd
from fastkml import kml
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, shape
from shapely.ops import unary_union, linemerge, polygonize, snap
import osmnx as ox
import ezdxf

# Konstanta
TARGET_EPSG = "EPSG:32760"
DEFAULT_WIDTH = 10

# ===============================
# Fungsi klasifikasi tipe jalan
# ===============================
def classify_layer(hwy):
    if hwy in ['motorway', 'trunk', 'primary']:
        return 'HIGHWAYS', 10
    elif hwy in ['secondary', 'tertiary']:
        return 'MAJOR_ROADS', 10
    elif hwy in ['residential', 'unclassified', 'service']:
        return 'MINOR_ROADS', 10
    elif hwy in ['footway', 'path', 'cycleway']:
        return 'PATHS', 10
    return 'OTHER', DEFAULT_WIDTH

# ===============================
# Ekstraksi polygon dari folder "BOUNDARY CLUSTER"
# ===============================
def extract_polygon_from_kml(kml_path):
    def extract_boundary_polygons_from_kml(file_path):
        with open(file_path, 'rb') as f:
            doc = f.read()
        k = kml.KML()
        k.from_string(doc)

        polygons = []

        def recursive_extract(features):
            for f in features:
                if isinstance(f, kml.Folder) and f.name.upper() == "BOUNDARY CLUSTER":
                    for sub in f.features():
                        if hasattr(sub, 'geometry') and sub.geometry:
                            geom = sub.geometry
                            if geom.geom_type in ["Polygon", "MultiPolygon"]:
                                polygons.append(shape(geom))
                elif hasattr(f, 'features'):
                    recursive_extract(f.features())

        recursive_extract(k.features())

        if not polygons:
            raise Exception("❌ Tidak ada polygon di folder 'BOUNDARY CLUSTER'.")
        return unary_union(polygons)

    if kml_path.endswith(".kmz"):
        with zipfile.ZipFile(kml_path) as zf:
            kml_filename = [n for n in zf.namelist() if n.endswith(".kml")][0]
            with zf.open(kml_filename) as kml_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as tmp_kml:
                    tmp_kml.write(kml_file.read())
                    tmp_kml.flush()
                    polygon = extract_boundary_polygons_from_kml(tmp_kml.name)
                    crs = "EPSG:4326"
                    return polygon, crs
    else:
        polygon = extract_boundary_polygons_from_kml(kml_path)
        crs = "EPSG:4326"
        return polygon, crs

# ===============================
# Ambil data jalan dari OSM
# ===============================
def get_osm_roads(polygon):
    tags = {"highway": True}
    roads = ox.features_from_polygon(polygon, tags=tags)
    roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])]
    roads = roads.explode(index_parts=False)
    roads = roads[~roads.geometry.is_empty & roads.geometry.notnull()]
    roads = roads.clip(polygon)
    roads["geometry"] = roads["geometry"].apply(lambda g: snap(g, g, tolerance=0.0001))
    roads = roads.reset_index(drop=True)
    return roads

# ===============================
# Hapus Z-coordinate dari geometri
# ===============================
def strip_z(geom):
    if geom.geom_type == "LineString" and geom.has_z:
        return LineString([(x, y) for x, y, *_ in geom.coords])
    elif geom.geom_type == "MultiLineString":
        return MultiLineString([
            LineString([(x, y) for x, y, *_ in line.coords]) if line.has_z else line
            for line in geom.geoms
        ])
    return geom

# ===============================
# Ekspor ke DXF
# ===============================
def export_to_dxf(gdf, dxf_path, polygon=None, polygon_crs=None):
    doc = ezdxf.new()
    msp = doc.modelspace()

    all_lines = []
    all_buffers = []
    buffer_layers = []

    for _, row in gdf.iterrows():
        geom = strip_z(row.geometry)
        hwy = str(row.get("highway", ""))
        layer, width = classify_layer(hwy)

        if geom.is_empty or not geom.is_valid:
            continue

        merged = geom if isinstance(geom, LineString) else linemerge(geom)

        if isinstance(merged, (LineString, MultiLineString)):
            buffered = merged.buffer(width / 2, resolution=8, join_style=2)
            all_lines.append(merged)
            all_buffers.append(buffered)
            buffer_layers.append(layer)

    if not all_buffers:
        raise Exception("❌ Tidak ada garis valid untuk diekspor.")

    all_union = unary_union(all_buffers)
    outlines = list(polygonize(all_union.boundary))
    if not outlines:
        raise Exception("❌ Polygonize gagal menghasilkan outline.")

    bounds = [(pt[0], pt[1]) for geom in outlines for pt in geom.exterior.coords]
    min_x = min(x for x, y in bounds)
    min_y = min(y for x, y in bounds)

    for outline in outlines:
        coords = [(pt[0] - min_x, pt[1] - min_y) for pt in outline.exterior.coords]
        msp.add_lwpolyline(coords, dxfattribs={"layer": "ROADS"})

    if polygon is not None and polygon_crs is not None:
        poly = gpd.GeoSeries([polygon], crs=polygon_crs).to_crs(TARGET_EPSG).iloc[0]
        if poly.geom_type == 'Polygon':
            coords = [(pt[0] - min_x, pt[1] - min_y) for pt in poly.exterior.coords]
            msp.add_lwpolyline(coords, dxfattribs={"layer": "BOUNDARY"})
        elif poly.geom_type == 'MultiPolygon':
            for p in poly.geoms:
                coords = [(pt[0] - min_x, pt[1] - min_y) for pt in p.exterior.coords]
                msp.add_lwpolyline(coords, dxfattribs={"layer": "BOUNDARY"})

    doc.set_modelspace_vport(height=10000)
    doc.saveas(dxf_path)

# ===============================
# Fungsi pemrosesan utama
# ===============================
def process_kml_to_dxf(kml_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    polygon, polygon_crs = extract_polygon_from_kml(kml_path)
    roads = get_osm_roads(polygon)

    geojson_path = os.path.join(output_dir, "roadmap_osm.geojson")
    dxf_path = os.path.join(output_dir, "roadmap_osm.dxf")

    if not roads.empty:
        roads_utm = roads.to_crs(TARGET_EPSG)
        roads_utm.to_file(geojson_path, driver="GeoJSON")
        export_to_dxf(roads_utm, dxf_path, polygon=polygon, polygon_crs=polygon_crs)
        return dxf_path, geojson_path, True
    else:
        raise Exception("Tidak ada jalan ditemukan di dalam area polygon.")

# ===============================
# Streamlit UI
# ===============================
st.set_page_config(page_title="Konversi KMZ/KML ke DXF", layout="centered")
st.title("📌 Konversi KML/KMZ (BOUNDARY CLUSTER) ke DXF + Jalan OSM")

uploaded_file = st.file_uploader("🗂️ Upload file KML atau KMZ", type=["kml", "kmz"])

if uploaded_file is not None:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, uploaded_file.name)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.read())

        with st.spinner("🔄 Memproses data dan mengambil peta jalan OSM..."):
            try:
                dxf_path, geojson_path, success = process_kml_to_dxf(input_path, tmpdir)
                st.success("✅ Konversi berhasil!")
                st.download_button("⬇️ Download DXF", open(dxf_path, "rb"), file_name="roadmap_osm.dxf")
                st.download_button("⬇️ Download GeoJSON", open(geojson_path, "rb"), file_name="roadmap_osm.geojson")
            except Exception as e:
                st.error(f"❌ Gagal: {str(e)}")
