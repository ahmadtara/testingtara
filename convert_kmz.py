# convert_kmz.py
import os
import zipfile
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from fastkml import kml
import osmnx as ox
import ezdxf

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S

def extract_polygon_from_kmz(kmz_path):
    # Ekstrak file KML dari KMZ
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

    recurse(k.features())

    if not polygons:
        raise Exception("No Polygon found in KML")

    return polygons[0]  # Ambil satu polygon pertama

def get_osm_roads(polygon: Polygon):
    roads = ox.features_from_polygon(polygon, tags={"highway": True})
    roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])]
    return roads

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

def process_kmz_to_dxf(kmz_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    polygon = extract_polygon_from_kmz(kmz_path)
    roads = get_osm_roads(polygon)
    roads_utm = roads.to_crs(TARGET_EPSG)

    geojson_path = os.path.join(output_dir, "roadmap_osm.geojson")
    dxf_path = os.path.join(output_dir, "roadmap_osm.dxf")

    roads_utm.to_file(geojson_path, driver="GeoJSON")
    export_to_dxf(roads_utm, dxf_path)

    return dxf_path, geojson_path
