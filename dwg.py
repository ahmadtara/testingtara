# [IMPORTS]
import streamlit as st
import os
import zipfile
from xml.etree import ElementTree as ET
import ezdxf
from pyproj import Transformer
import geopandas as gpd
from fastkml import kml
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union, linemerge, polygonize, snap
import osmnx as ox

# ======================== KMZ to DXF (Autocad Template) ========================

transformer = Transformer.from_crs("EPSG:4326", "EPSG:32760", always_xy=True)
target_folders = {
    'FDT', 'FAT', 'HP COVER', 'NEW POLE 7-3', 'NEW POLE 7-4',
    'EXISTING POLE EMR 7-4', 'EXISTING POLE EMR 7-3',
    'BOUNDARY', 'DISTRIBUTION CABLE', 'SLING WIRE', 'KOTAK'
}

# [Functions for KMZ Processing: extract_kmz, parse_kml, latlon_to_xy, etc...]
# [Full function bodies retained from your original code]
# ... COPY ALL FUNCTION DEFINITIONS RELATED TO KMZ PROCESSING FROM YOUR CODE HERE ...

# ======================== KML to Road DXF (OSM) ========================

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

def extract_polygon_from_kml(kml_path):
    gdf = gpd.read_file(kml_path)
    polygons = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if polygons.empty:
        raise Exception("No Polygon found in KML")
    return unary_union(polygons.geometry), polygons.crs

def get_osm_roads(polygon):
    tags = {"highway": True}
    roads = ox.features_from_polygon(polygon, tags=tags)
    roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])].explode(index_parts=False)
    roads = roads[roads.geometry.notnull() & ~roads.geometry.is_empty].clip(polygon)
    roads["geometry"] = roads["geometry"].apply(lambda g: snap(g, g, tolerance=0.0001))
    return roads.reset_index(drop=True)

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
    buffer_layers = []

    for _, row in gdf.iterrows():
        geom = strip_z(row.geometry)
        hwy = str(row.get("highway", ""))
        layer, width = classify_layer(hwy)

        if geom.is_empty or not geom.is_valid:
            continue

        merged = geom if isinstance(geom, LineString) else linemerge(geom)
        if
