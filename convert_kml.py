import os
import zipfile
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, MultiLineString
from fastkml import kml
import osmnx as ox
import ezdxf
from shapely.ops import unary_union, linemerge, snap
import pandas as pd

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S

# Lebar jalan default mirip CadMapper
DEFAULT_WIDTH = 6


def classify_layer(hwy):
    if hwy in ['motorway', 'trunk', 'primary']:
        return 'HIGHWAYS', 24
    if hwy in ['secondary', 'tertiary']:
        return 'MAJOR_ROADS', 14
    if hwy in ['residential', 'unclassified', 'service']:
        return 'MINOR_ROADS', 8
    if hwy in ['footway', 'path', 'cycleway']:
        return 'PATHS', 4
    return 'OTHER', DEFAULT_WIDTH


def get_dynamic_width(row):
    try:
        if 'width' in row and pd.notnull(row['width']):
            return float(row['width'])
        if 'lanes' in row and pd.notnull(row['lanes']):
            return float(row['lanes']) * 3.5
    except:
        pass
    _, default = classify_layer(row.get('highway', ''))
    return default


def extract_polygon_from_kml(kml_path):
    gdf = gpd.read_file(kml_path)
    polygons = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if polygons.empty:
        raise Exception("No Polygon found in KML")
    return unary_union(polygons.geometry)


def get_osm_roads(polygon):
    try:
        tags = {"highway": True, "width": True, "lanes": True}
        roads = ox.features_from_polygon(polygon, tags=tags)
        roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])]
        roads = roads.explode(index_parts=False)
        roads = roads[~roads.geometry.is_empty & roads.geometry.notnull()]
        roads = roads.dropna(subset=['geometry'])
        roads["geometry"] = roads["geometry"].apply(lambda g: snap(g, g, tolerance=0.0001))
        roads = roads.reset_index(drop=True)
        return roads
    except Exception as e:
        print("Error fetching roads:", e)
        return gpd.GeoDataFrame()


def offset_lines(line: LineString, width: float):
    try:
        left = line.parallel_offset(width / 2, side='left', resolution=32, join_style=2)
        right = line.parallel_offset(width / 2, side='right', resolution=32, join_style=2)
        return left, right
    except Exception:
        return None, None


def export_to_dxf(gdf, dxf_path):
    doc = ezdxf.new()
    msp = doc.modelspace()

    all_lines = []
    for idx, row in gdf.iterrows():
        geom = row.geometry
        hwy = str(row.get("highway", "unknown"))
        width = get_dynamic_width(row)
        layer, _ = classify_layer(hwy)

        if geom.geom_type == "LineString":
            left, right = offset_lines(geom, width)
            if left and right:
                all_lines.extend([(left, layer), (right, layer)])

        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                left, right = offset_lines(line, width)
                if left and right:
                    all_lines.extend([(left, layer), (right, layer)])

    all_coords = []
    for line, _ in all_lines:
        if line and hasattr(line, "coords"):
            all_coords.extend(line.coords)

    if not all_coords:
        raise Exception("❌ Tidak ada garis valid untuk diekspor.")

    min_x = min(x for x, y in all_coords)
    min_y = min(y for x, y in all_coords)

    for line, layer in all_lines:
        if line and hasattr(line, "coords"):
            shifted = [(x - min_x, y - min_y) for x, y in line.coords]
            if len(shifted) > 1:
                msp.add_lwpolyline(shifted, dxfattribs={"layer": layer})

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
        export_to_dxf(roads_utm, dxf_path)
        return dxf_path, geojson_path, True
    else:
        raise Exception("Tidak ada jalan ditemukan di dalam area polygon.")
