# convert_kml.py
import os
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString
from fastkml import kml
import osmnx as ox
import ezdxf
import streamlit as st

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S

def extract_polygon_from_kml(kml_path):
    with open(kml_path, 'rt', encoding='utf-8') as file:
        doc = file.read()

    k = kml.KML()
    k.from_string(doc)

    # Debug struktur isi KML
    st.code(k.to_string(prettyprint=True), language="xml")

    polygons = []

    def extract_polygons(geom):
        if isinstance(geom, Polygon):
            polygons.append(geom)
        elif isinstance(geom, MultiPolygon):
            polygons.extend(list(geom.geoms))
        elif isinstance(geom, GeometryCollection):
            for g in geom.geoms:
                extract_polygons(g)
        elif isinstance(geom, LineString):
            if geom.is_ring:
                polygons.append(Polygon(geom))

    def recurse(feats):
        for feat in feats:
            # Cari fitur di dalam struktur nested (Document, Folder, dst)
            try:
                subfeats = list(feat.features()) if callable(feat.features) else list(feat.features)
                recurse(subfeats)
            except Exception:
                pass
            if hasattr(feat, "geometry") and feat.geometry is not None:
                extract_polygons(feat.geometry)

    recurse(k.features)

    if not polygons:
        raise Exception("No Polygon or closed LineString found in KML")

    return polygons[0]

def get_osm_roads(polygon: Polygon):
    try:
        roads = ox.features_from_polygon(polygon, tags={"highway": True})
        roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])]
        return roads
    except Exception:
        return gpd.GeoDataFrame()

def export_to_dxf(gdf, dxf_path):
    doc = ezdxf.new()
    msp = doc.modelspace()
    for geom in gdf.geometry:
        if geom.geom_type == "LineString":
            msp.add_lwpolyline(list(geom.coords))
        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                msp.add_lwpolyline(list(line.coords))
    doc.saveas(dxf_path)

def process_kml_to_dxf(kml_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    polygon = extract_polygon_from_kml(kml_path)
    roads = get_osm_roads(polygon)

    geojson_path = os.path.join(output_dir, "roadmap_osm.geojson")
    dxf_path = os.path.join(output_dir, "roadmap_osm.dxf")

    if roads.empty:
        raise Exception("Tidak ada jalan ditemukan di dalam area polygon.")

    roads_utm = roads.to_crs(TARGET_EPSG)
    roads_utm.to_file(geojson_path, driver="GeoJSON")
    export_to_dxf(roads_utm, dxf_path)

    return dxf_path, geojson_path, True
