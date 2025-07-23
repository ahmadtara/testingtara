import os
import zipfile
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, MultiLineString
from fastkml import kml
import osmnx as ox
import ezdxf
from shapely.ops import unary_union, linemerge, snap, split, polygonize
import pandas as pd
import streamlit as st

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S
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

def extract_polygon_from_kml(kml_path):
    gdf = gpd.read_file(kml_path)
    polygons = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if polygons.empty:
        raise Exception("No Polygon found in KML")
    return unary_union(polygons.geometry), polygons.crs

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

def export_to_dxf(gdf, dxf_path, polygon=None, polygon_crs=None):
    doc = ezdxf.new()
    msp = doc.modelspace()

    grouped = {}
    for _, row in gdf.iterrows():
        geom = row.geometry
        hwy = str(row.get("highway", ""))
        layer, width = classify_layer(hwy)

        if geom.is_empty or not geom.is_valid:
            continue

        if layer not in grouped:
            grouped[layer] = {"geoms": [], "width": width}
        grouped[layer]["geoms"].append(geom)

    all_bounds = []
    outlines_by_layer = {}

    for layer, data in grouped.items():
        merged = linemerge(unary_union(data["geoms"]))
        if isinstance(merged, LineString):
            merged = [merged]
        elif isinstance(merged, (MultiLineString, GeometryCollection)):
            merged = [g for g in merged.geoms if isinstance(g, LineString)]

        buffered = unary_union([g.buffer(data["width"] / 2, resolution=8, join_style=2) for g in merged])
        outlines = []
        if buffered.geom_type == 'Polygon':
            outlines = [buffered.exterior]
        elif buffered.geom_type == 'MultiPolygon':
            outlines = [p.exterior for p in buffered.geoms if p.exterior is not None]

        outlines_by_layer[layer] = outlines
        all_bounds.extend([pt for outline in outlines for pt in outline.coords])

    if not all_bounds:
        raise Exception("❌ Tidak ada garis valid untuk diekspor.")

    min_x = min(p[0] for p in all_bounds)
    min_y = min(p[1] for p in all_bounds)

    for layer, outlines in outlines_by_layer.items():
        for outline in outlines:
            coords = [(x - min_x, y - min_y) for x, y in outline.coords]
            msp.add_lwpolyline(coords, dxfattribs={"layer": layer})

    if polygon is not None and polygon_crs is not None:
        poly = gpd.GeoSeries([polygon], crs=polygon_crs).to_crs(TARGET_EPSG).iloc[0]
        if poly.geom_type == 'Polygon':
            coords = [(x - min_x, y - min_y) for x, y in poly.exterior.coords]
            msp.add_lwpolyline(coords, dxfattribs={"layer": "BOUNDARY"})
        elif poly.geom_type == 'MultiPolygon':
            for p in poly.geoms:
                coords = [(x - min_x, y - min_y) for x, y in p.exterior.coords]
                msp.add_lwpolyline(coords, dxfattribs={"layer": "BOUNDARY"})

    doc.set_modelspace_vport(height=10000)
    doc.saveas(dxf_path)

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

# Streamlit UI
st.set_page_config(page_title="KML → DXF Road Converter", layout="wide")
st.title("🌍 KML → DXF Road Converter")
st.caption("Upload file .KML (area batas cluster)")

kml_file = st.file_uploader("Upload file .KML", type=["kml"])

if kml_file:
    with st.spinner("🛁 Memproses file..."):
        try:
            temp_input = f"/tmp/{kml_file.name}"
            with open(temp_input, "wb") as f:
                f.write(kml_file.read())

            output_dir = "/tmp/output"
            dxf_path, geojson_path, ok = process_kml_to_dxf(temp_input, output_dir)

            if ok:
                st.success("✅ Berhasil diekspor ke DXF!")
                with open(dxf_path, "rb") as f:
                    st.download_button("⬇️ Download DXF", data=f, file_name="roadmap_osm.dxf")
                with open(geojson_path, "rb") as f:
                    st.download_button("⬇️ Download GeoJSON", data=f, file_name="roadmap_osm.geojson")
        except Exception as e:
            st.error(f"❌ Terjadi kesalahan: {e}")
