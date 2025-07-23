# convert_kml.py
import os
import geopandas as gpd
from shapely.geometry import Polygon
from lxml import etree
import osmnx as ox
import ezdxf

TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S

def extract_polygon_from_kml(kml_path):
    with open(kml_path, 'rt', encoding='utf-8') as f:
        tree = etree.parse(f)

    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    coords = tree.xpath('//kml:Polygon/kml:outerBoundaryIs/kml:LinearRing/kml:coordinates', namespaces=ns)

    if not coords:
        raise Exception("❌ Polygon <coordinates> not found in KML.")

    coord_text = coords[0].text.strip()
    point_list = []
    for line in coord_text.split():
        parts = line.strip().split(',')
        if len(parts) >= 2:
            lon, lat = float(parts[0]), float(parts[1])
            point_list.append((lon, lat))

    if len(point_list) < 3:
        raise Exception("❌ Not enough points to form a polygon.")

    return Polygon(point_list)

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

    if gdf.empty:
        raise Exception("❌ Tidak ada geometri yang dapat diekspor ke DXF.")

    # Dapatkan offset agar objek terlihat dekat (0,0)
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    offset_x, offset_y = bounds[0], bounds[1]

    for geom in gdf.geometry:
        if geom.geom_type == "LineString":
            shifted = [(x - offset_x, y - offset_y) for x, y in geom.coords]
            msp.add_lwpolyline(shifted)
        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                shifted = [(x - offset_x, y - offset_y) for x, y in line.coords]
                msp.add_lwpolyline(shifted)

    # Tambahkan label tengah (opsional)
    center_x = (bounds[0] + bounds[2]) / 2 - offset_x
    center_y = (bounds[1] + bounds[3]) / 2 - offset_y
    msp.add_text("CENTER", dxfattribs={'height': 5}).set_pos((center_x, center_y))

    doc.saveas(dxf_path)

def process_kml_to_dxf(kml_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    polygon = extract_polygon_from_kml(kml_path)
    roads = get_osm_roads(polygon)

    geojson_path = os.path.join(output_dir, "roadmap_osm.geojson")
    dxf_path = os.path.join(output_dir, "roadmap_osm.dxf")

    if roads.empty:
        raise Exception("⚠️ Tidak ada jalan ditemukan di dalam area polygon.")

    roads_utm = roads.to_crs(TARGET_EPSG)
    roads_utm.to_file(geojson_path, driver="GeoJSON")
    export_to_dxf(roads_utm, dxf_path)

    return dxf_path, geojson_path, True
