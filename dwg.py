import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET
import geopandas as gpd
import streamlit as st
import ezdxf
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, MultiLineString
from shapely.ops import unary_union
import osmnx as ox
from pyproj import Transformer

TARGET_EPSG = "EPSG:32760"
DEFAULT_WIDTH = 10


def extract_kml_from_kmz(kmz_path, target_folder="BOUNDARY CLUSTER"):
    with zipfile.ZipFile(kmz_path, 'r') as zip_ref:
        extract_dir = tempfile.mkdtemp()
        zip_ref.extractall(extract_dir)
        for root, dirs, files in os.walk(extract_dir):
            if target_folder.lower() in root.lower():
                for file in files:
                    if file.endswith(".kml"):
                        return os.path.join(root, file)
    raise FileNotFoundError(f"Tidak ditemukan file KML di folder {target_folder}")


def get_osm_streets_from_polygon(polygon):
    if polygon is None or polygon.is_empty:
        raise ValueError("Polygon tidak ditemukan atau kosong")

    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    # Transformasi polygon ke EPSG:4326 (lat/lon) sebelum digunakan oleh osmnx
    transformer = Transformer.from_crs(TARGET_EPSG, "EPSG:4326", always_xy=True)

    def transform_geom(geom):
        if geom.geom_type == 'Polygon':
            return Polygon([transformer.transform(x, y) for x, y in geom.exterior.coords])
        elif geom.geom_type == 'MultiPolygon':
            return MultiPolygon([
                Polygon([transformer.transform(x, y) for x, y in poly.exterior.coords])
                for poly in geom.geoms
            ])
        else:
            raise ValueError("Tipe geometry tidak didukung: " + geom.geom_type)

    polygon_wgs84 = transform_geom(polygon)

    tags = {"highway": True}
    gdf = ox.geometries.geometries_from_polygon(polygon_wgs84, tags)
    return gdf[gdf.geometry.type.isin(["LineString", "MultiLineString"])]


def export_to_dxf(gdf, dxf_path, polygon=None, polygon_crs=None):
    doc = ezdxf.new()
    msp = doc.modelspace()

    for _, row in gdf.iterrows():
        geom = row.geometry
        if isinstance(geom, LineString):
            points = list(geom.coords)
            msp.add_lwpolyline(points, dxfattribs={"layer": "OSM"})
        elif isinstance(geom, MultiLineString):
            for line in geom:
                points = list(line.coords)
                msp.add_lwpolyline(points, dxfattribs={"layer": "OSM"})

    if polygon is not None:
        if polygon_crs is None:
            polygon_crs = "EPSG:4326"
        if polygon_crs != TARGET_EPSG:
            polygon = gpd.GeoSeries([polygon], crs=polygon_crs).to_crs(TARGET_EPSG).iloc[0]
        if isinstance(polygon, (Polygon, MultiPolygon)):
            if isinstance(polygon, Polygon):
                msp.add_lwpolyline(list(polygon.exterior.coords), dxfattribs={"layer": "BOUNDARY"})
            else:
                for poly in polygon.geoms:
                    msp.add_lwpolyline(list(poly.exterior.coords), dxfattribs={"layer": "BOUNDARY"})

    doc.saveas(dxf_path)


def process_kmz_to_dxf(kmz_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    kml_path = extract_kml_from_kmz(kmz_path, target_folder="BOUNDARY CLUSTER")

    gdf = gpd.read_file(kml_path)
    polygon = unary_union(gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].geometry)
    polygon_crs = gdf.crs
    if polygon_crs is None:
        polygon_crs = "EPSG:4326"

    roads = get_osm_streets_from_polygon(polygon)

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
    st.title("🌍 KMZ → DXF Road Converter")
    st.caption("Upload file .KMZ yang memiliki folder 'BOUNDARY CLUSTER' untuk ambil polygon area")

    kmz_file = st.file_uploader("Upload file .KMZ", type=["kmz"])

    if kmz_file:
        with st.spinner("💫 Memproses file..."):
            try:
                temp_input = f"/tmp/{kmz_file.name}"
                with open(temp_input, "wb") as f:
                    f.write(kmz_file.read())

                output_dir = "/tmp/output"
                dxf_path, geojson_path, ok = process_kmz_to_dxf(temp_input, output_dir)

                if ok:
                    st.success("✅ Berhasil diekspor ke DXF!")
                    with open(dxf_path, "rb") as f:
                        st.download_button("⬇️ Download Jalan Autocad UTM 60", data=f, file_name="roadmap_osm.dxf")
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan: {e}")


if __name__ == "__main__":
    run_kmz_dxf()
