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
DEFAULT_WIDTH = 6
MIN_LINE_LENGTH = 1.0  # meter


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
        tags = {"highway": True}  # Ambil semua jalan
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


def export_to_dxf(gdf, dxf_path):
    doc = ezdxf.new()
    msp = doc.modelspace()

    grouped_buffers = {}
    all_lines = []

    # Merge seluruh geometri ke satu layer dulu untuk simpang otomatis
    all_merged = linemerge(unary_union(gdf.geometry))

    if isinstance(all_merged, (GeometryCollection, MultiLineString)):
        all_lines = [g for g in all_merged.geoms if isinstance(g, LineString) and g.length >= MIN_LINE_LENGTH]
    elif isinstance(all_merged, LineString):
        all_lines = [all_merged] if all_merged.length >= MIN_LINE_LENGTH else []

    for line in all_lines:
        if not line.is_valid or line.is_empty:
            continue
        # Ambil atribut jalan berdasarkan kedekatan (nearest)
        nearest = gdf.distance(gpd.GeoSeries([line])).idxmin()
        row = gdf.loc[nearest]

        hwy = str(row.get("highway", "unknown"))
        width = get_dynamic_width(row)
        layer, _ = classify_layer(hwy)

        try:
            buffer = line.buffer(width / 2, resolution=8, join_style=2)
            if buffer.is_empty or not buffer.is_valid:
                continue
            if layer not in grouped_buffers:
                grouped_buffers[layer] = []
            grouped_buffers[layer].append(buffer)
        except:
            continue

    if not grouped_buffers:
        raise Exception("❌ Tidak ada garis valid untuk diekspor.")

    min_x = min((geom.bounds[0] for buffers in grouped_buffers.values() for geom in buffers), default=0)
    min_y = min((geom.bounds[1] for buffers in grouped_buffers.values() for geom in buffers), default=0)

    for layer, buffers in grouped_buffers.items():
        union = unary_union(buffers)
        outlines = []

        if union.geom_type == 'Polygon':
            outlines = [union.exterior]
        elif union.geom_type == 'MultiPolygon':
            outlines = [poly.exterior for poly in union.geoms if poly.exterior is not None]
        elif union.geom_type == 'GeometryCollection':
            outlines = [g.exterior for g in union.geoms if hasattr(g, 'exterior') and g.exterior is not None]

        for outline in outlines:
            if outline is None:
                continue
            shifted = [(x - min_x, y - min_y) for x, y in outline.coords]
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
