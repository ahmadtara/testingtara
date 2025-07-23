""import os
import zipfile
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, MultiLineString
from fastkml import kml
import osmnx as ox
import ezdxf
from shapely.ops import unary_union, linemerge, snap

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S

# Lebar jalan untuk tipe-tipe OSM
ROAD_WIDTHS = {
    "motorway": 10,
    "trunk": 10,
    "primary": 10,
    "secondary": 10,
    "tertiary": 10,
    "residential": 10,
    "service": 10,
    "unclassified": 10,
    "footway": 10,
    "cycleway": 10,
    "path": 10,
}

def extract_polygon_from_kml(kml_path):
    gdf = gpd.read_file(kml_path)
    polygons = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]

    if polygons.empty:
        raise Exception("No Polygon found in KML")

    return unary_union(polygons.geometry)

def get_osm_roads(polygon):
    try:
        tags = {"highway": True}
        roads = ox.features_from_polygon(polygon, tags=tags)
        roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])]
        roads = roads.explode(index_parts=False)
        roads["geometry"] = roads["geometry"].apply(lambda g: snap(g, g, tolerance=0.0001))
        return roads
    except Exception:
        return gpd.GeoDataFrame()

def offset_lines(line: LineString, width: float):
    try:
        left = line.parallel_offset(width / 2, side='left', resolution=16, join_style=2)
        right = line.parallel_offset(width / 2, side='right', resolution=16, join_style=2)
        return left, right
    except Exception:
        return line, line

def export_to_dxf(gdf, dxf_path):
    doc = ezdxf.new()
    msp = doc.modelspace()

    all_lines = []

    for idx, row in gdf.iterrows():
        geom = row.geometry
        highway_type = str(row.get("highway", "unknown"))
        width = ROAD_WIDTHS.get(highway_type, 10)
        layer_name = highway_type.upper()

        if geom.geom_type == "LineString":
            left, right = offset_lines(geom, width)
            all_lines.extend([(left, layer_name), (right, layer_name)])

        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                left, right = offset_lines(line, width)
                all_lines.extend([(left, layer_name), (right, layer_name)])

    all_coords = []
    for line, _ in all_lines:
        if line and hasattr(line, "coords"):
            all_coords.extend(line.coords)

    if not all_coords:
        raise Exception("Tidak ada garis valid untuk diekspor.")

    xs, ys = zip(*all_coords)
    min_x, min_y = min(xs), min(ys)

    for line, layer_name in all_lines:
        if line and hasattr(line, "coords"):
            shifted_coords = [(x - min_x, y - min_y) for x, y in line.coords]
            if len(shifted_coords) > 1:
                msp.add_lwpolyline(shifted_coords, dxfattribs={"layer": layer_name})

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
        jalan_ditemukan = True
    else:
        jalan_ditemukan = False
        raise Exception("Tidak ada jalan ditemukan di dalam area polygon.")

    return dxf_path, geojson_path, jalan_ditemukan
