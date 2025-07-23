import os
import zipfile
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, MultiLineString
from fastkml import kml
import osmnx as ox
import ezdxf
from shapely.ops import unary_union, linemerge, snap, split, polygonize
import pandas as pd

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S
DEFAULT_WIDTH = 10
MIN_LINE_LENGTH = 1.0  # meter


def classify_layer(hwy):
    return 'ROADS', DEFAULT_WIDTH


def get_dynamic_width(row):
    return DEFAULT_WIDTH


def extract_polygon_from_kml(kml_path):
    gdf = gpd.read_file(kml_path)
    polygons = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if polygons.empty:
        raise Exception("No Polygon found in KML")
    return unary_union(polygons.geometry)


def get_osm_roads(polygon):
    try:
        tags = {"highway": True}  # Ambil semua jalan
        roads = ox.features_from_polygon(polygon, tags=tags)
        roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])]
        roads = roads.explode(index_parts=False)
        roads = roads[~roads.geometry.is_empty & roads.geometry.notnull()]
        roads = roads.dropna(subset=['geometry'])
        roads = roads.clip(polygon)  # pastikan hanya dalam polygon
        roads["geometry"] = roads["geometry"].apply(lambda g: snap(g, g, tolerance=0.0001))
        roads = roads.reset_index(drop=True)
        return roads
    except Exception as e:
        print("Error fetching roads:", e)
        return gpd.GeoDataFrame()


def clean_intersections(lines):
    merged = linemerge(unary_union(lines))
    if isinstance(merged, LineString):
        merged = [merged]
    elif isinstance(merged, (MultiLineString, GeometryCollection)):
        merged = [g for g in merged.geoms if isinstance(g, LineString)]
    return merged


def export_to_dxf(gdf, dxf_path, polygon=None):
    doc = ezdxf.new()
    msp = doc.modelspace()

    all_lines = clean_intersections(gdf.geometry)
    if not all_lines:
        raise Exception("❌ Tidak ada garis valid untuk diekspor.")

    # Gabungkan dan offset secara global
    full_union = unary_union(all_lines)
    full_buffer = full_union.buffer(DEFAULT_WIDTH / 2, resolution=8, join_style=2)

    if full_buffer.is_empty:
        raise Exception("❌ Buffer kosong. Tidak ada outline jalan.")

    if full_buffer.geom_type == 'Polygon':
        outlines = [full_buffer.exterior]
    elif full_buffer.geom_type == 'MultiPolygon':
        outlines = [poly.exterior for poly in full_buffer.geoms if poly.exterior is not None]
    else:
        outlines = []

    min_x, min_y = float('inf'), float('inf')
    for outline in outlines:
        for x, y in outline.coords:
            min_x = min(min_x, x)
            min_y = min(min_y, y)

    for outline in outlines:
        coords = [(x - min_x, y - min_y) for x, y in outline.coords]
        msp.add_lwpolyline(coords, dxfattribs={"layer": "ROADS"})

    # Tambahkan boundary polygon ke layer "BOUNDARY"
    if polygon:
        if polygon.geom_type == 'Polygon':
            exterior = polygon.exterior
            coords = [(x - min_x, y - min_y) for x, y in exterior.coords]
            msp.add_lwpolyline(coords, dxfattribs={"layer": "BOUNDARY"})
        elif polygon.geom_type == 'MultiPolygon':
            for p in polygon.geoms:
                coords = [(x - min_x, y - min_y) for x, y in p.exterior.coords]
                msp.add_lwpolyline(coords, dxfattribs={"layer": "BOUNDARY"})

    doc.set_modelspace_vport(height=10000)
    doc.saveas(dxf_path)


def process_kml_to_dxf(kml_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    polygon = extract_polygon_from_kml(kml_path)
    roads = get_osm_roads(polygon)

    geojson_path = os.path.join(output_dir, "roadmap_osm.geojson")
    dxf_path = os.path.join(output_dir, "roadmap_osm.dxf")

    if not roads.empty:
        roads_utm = roads.to_crs(TARGET_EPSG)
        roads_utm.to_file(geojson_path, driver="GeoJSON")
        export_to_dxf(roads_utm, dxf_path, polygon=polygon.to_crs(TARGET_EPSG))
        return dxf_path, geojson_path, True
    else:
        raise Exception("Tidak ada jalan ditemukan di dalam area polygon.")
