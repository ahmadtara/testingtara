import os
import zipfile
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString
from fastkml import kml
import osmnx as ox
import ezdxf

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S

def extract_polygon_from_kmz(kmz_path):
    with zipfile.ZipFile(kmz_path, 'r') as zf:
        for f in zf.namelist():
            if f.endswith('.kml'):
                zf.extract(f, "/tmp")
                kml_path = os.path.join("/tmp", f)
                break
        else:
            raise Exception("KML file not found in KMZ")

    with open(kml_path, 'rt', encoding='utf-8') as file:
        doc = file.read()

    k = kml.KML()
    k.from_string(doc)

    polygons = []

    def extract_polygons(geom):
        if isinstance(geom, Polygon):
            polygons.append(geom)
        elif isinstance(geom, MultiPolygon):
            polygons.extend(list(geom.geoms))
        elif isinstance(geom, GeometryCollection):
            for g in geom.geoms:
                extract_polygons(g)

    def recurse(feats):
        for feat in list(feats):
            if hasattr(feat, "geometry") and feat.geometry is not None:
                extract_polygons(feat.geometry)
            if hasattr(feat, "features"):
                recurse(feat.features)

    recurse(k.features)

    if not polygons:
        raise Exception("No Polygon found in KML")

    return polygons[0]

def get_osm_roads(polygon: Polygon):
    try:
        roads = ox.features_from_polygon(polygon, tags={"highway": True})
        roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])]
        return roads
    except Exception:
        return gpd.GeoDataFrame()

def offset_lines(line, width):
    if not isinstance(line, LineString):
        return []
    offset = width / 2
    left = line.parallel_offset(offset, 'left', join_style=2)
    right = line.parallel_offset(offset, 'right', join_style=2)
    if left.is_empty or right.is_empty:
        return []
    return [left, right]

def export_to_dxf_outline(gdf, dxf_path):
    doc = ezdxf.new()
    msp = doc.modelspace()

    if gdf.empty:
        raise Exception("❌ Tidak ada geometri jalan.")

    bounds = gdf.total_bounds
    offset_x, offset_y = bounds[0], bounds[1]

    def classify(highway_type):
        if highway_type in ['motorway', 'trunk', 'primary']:
            return 'HIGHWAY', 10
        elif highway_type in ['secondary', 'tertiary']:
            return 'MAJOR', 10
        elif highway_type in ['residential', 'unclassified', 'service']:
            return 'MINOR', 10
        elif highway_type in ['footway', 'path', 'cycleway']:
            return 'PATH', 10
        else:
            return 'OTHER', 5

    for idx, row in gdf.iterrows():
        geom = row.geometry
        highway = str(row.get('highway', 'other'))
        layer, width = classify(highway)

        lines = []
        if geom.geom_type == "LineString":
            lines.extend(offset_lines(geom, width))
        elif geom.geom_type == "MultiLineString":
            for l in geom.geoms:
                lines.extend(offset_lines(l, width))

        for outline in lines:
            coords = [(x - offset_x, y - offset_y) for x, y in outline.coords]
            msp.add_lwpolyline(coords, dxfattribs={"layer": layer})

    doc.saveas(dxf_path)

def process_kmz_to_dxf(kmz_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    polygon = extract_polygon_from_kmz(kmz_path)
    roads = get_osm_roads(polygon)

    geojson_path = os.path.join(output_dir, "roadmap_osm.geojson")
    dxf_path = os.path.join(output_dir, "roadmap_osm.dxf")

    if not roads.empty:
        roads_utm = roads.to_crs(TARGET_EPSG)
        roads_utm.to_file(geojson_path, driver="GeoJSON")
        export_to_dxf_outline(roads_utm, dxf_path)
        jalan_ditemukan = True
    else:
        jalan_ditemukan = False
        raise Exception("Tidak ada jalan ditemukan di dalam area polygon.")

    return dxf_path, geojson_path, jalan_ditemukan
