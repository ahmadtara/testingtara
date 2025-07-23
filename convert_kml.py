import os
import zipfile
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, MultiLineString
from fastkml import kml
import osmnx as ox
import ezdxf
from shapely.ops import unary_union

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
    with open(kml_path, 'rb') as file:
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

    return unary_union(polygons)


def get_osm_roads(polygon):
    try:
        tags = {"highway": True}
        roads = ox.features_from_polygon(polygon, tags=tags)
        roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])]
        return roads
    except Exception:
        return gpd.GeoDataFrame()


def offset_lines(line: LineString, width: float):
    try:
        left = line.parallel_offset(width / 2, side='left', resolution=2, join_style=2)
        right = line.parallel_offset(width / 2, side='right', resolution=2, join_style=2)
        return left, right
    except Exception:
        return line, line


def export_to_dxf(gdf, dxf_path):
    doc = ezdxf.new()
    msp = doc.modelspace()

    for idx, row in gdf.iterrows():
        geom = row.geometry
        highway_type = row.get("highway", "unknown")
        width = ROAD_WIDTHS.get(highway_type, 10)

        if geom.geom_type == "LineString":
            left, right = offset_lines(geom, width)
            msp.add_lwpolyline(list(left.coords), dxfattribs={"layer": highway_type})
            msp.add_lwpolyline(list(right.coords), dxfattribs={"layer": highway_type})

        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                left, right = offset_lines(line, width)
                msp.add_lwpolyline(list(left.coords), dxfattribs={"layer": highway_type})
                msp.add_lwpolyline(list(right.coords), dxfattribs={"layer": highway_type})

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
