import os
import zipfile
from fastkml import kml
import geopandas as gpd
import streamlit as st
import ezdxf
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, MultiLineString
from shapely.ops import unary_union, linemerge, snap, polygonize
import osmnx as ox
from tempfile import NamedTemporaryFile

TARGET_EPSG = "EPSG:32760"
DEFAULT_WIDTH = 10

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

def extract_polygon_from_kmz(kmz_path):
    with zipfile.ZipFile(kmz_path, 'r') as zf:
        kml_files = [f for f in zf.namelist() if f.endswith('.kml')]
        if not kml_files:
            raise Exception("KMZ tidak berisi file KML.")

        with zf.open(kml_files[0], 'r') as kmlfile:
            gdf = gpd.read_file(kmlfile)
            gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
            gdf = gdf[gdf['Name'].str.upper().str.contains("BOUNDARY CLUSTER")]
            if gdf.empty:
                raise Exception("Tidak ada polygon dari folder 'BOUNDARY CLUSTER' ditemukan.")
            return unary_union(gdf.geometry), gdf.crs

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

def strip_z(geom):
    if geom.geom_type == "LineString" and geom.has_z:
        return LineString([(x, y) for x, y, *_ in geom.coords])
    elif geom.geom_type == "MultiLineString":
        return MultiLineString([
            LineString([(x, y) for x, y, *_ in line.coords]) if line.has_z else line
            for line in geom.geoms
        ])
    return geom

def export_to_dxf(gdf, dxf_path, polygon=None, polygon_crs=None):
    doc = ezdxf.new()
    msp = doc.modelspace()

    all_buffers = []

    for _, row in gdf.iterrows():
        geom = strip_z(row.geometry)
        hwy = str(row.get("highway", ""))
        layer, width = classify_layer(hwy)

        if geom.is_empty or not geom.is_valid:
            continue

        merged = linemerge(geom) if not isinstance(geom, LineString) else geom

        if isinstance(merged, (LineString, MultiLineString)):
            buffered = merged.buffer(width / 2, resolution=8, join_style=2)
            all_buffers.append(buffered)

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
        polys = [poly] if poly.geom_type == 'Polygon' else poly.geoms
        for p in polys:
            coords = [(pt[0] - min_x, pt[1] - min_y) for pt in p.exterior.coords]
            msp.add_lwpolyline(coords, dxfattribs={"layer": "BOUNDARY_CLUSTER"})

    doc.set_modelspace_vport(height=10000)
    doc.saveas(dxf_path)

def process_kmz_to_dxf(kmz_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    polygon, polygon_crs = extract_polygon_from_kmz(kmz_path)
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

def run_kmz_dxf():
    st.title("🌍 KMZ → DXF Road Converter (BOUNDARY CLUSTER)")
    st.caption("Upload file .KMZ yang berisi folder 'BOUNDARY CLUSTER'")
    kmz_file = st.file_uploader("Upload file .KMZ", type=["kmz"])

    if kmz_file:
        with st.spinner("💫 Memproses file..."):
            try:
                with NamedTemporaryFile(delete=False, suffix=".kmz") as temp_kmz:
                    temp_kmz.write(kmz_file.read())
                    temp_kmz_path = temp_kmz.name

                output_dir = "/tmp/output_kmz"
                dxf_path, geojson_path, ok = process_kmz_to_dxf(temp_kmz_path, output_dir)

                if ok:
                    st.success("✅ Berhasil diekspor ke DXF!")
                    with open(dxf_path, "rb") as f:
                        st.download_button("⬇️ Download Jalan Autocad UTM 60", data=f, file_name="roadmap_osm.dxf")

            except Exception as e:
                st.error(f"❌ Terjadi kesalahan: {e}")

if __name__ == "__main__":
    run_kmz_dxf()
