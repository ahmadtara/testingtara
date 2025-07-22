import os
import zipfile
import geopandas as gpd
from shapely.geometry import Polygon
from fastkml import kml
import osmnx as ox
import ezdxf

# === Konfigurasi ===
KMZ_FILE = os.path.join("BOUNDARY CLUSTER", "Untitled Polygon.kmz")
OUTPUT_DIR = "output"
TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S (Indonesia Timur)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# === Ekstrak Poligon dari KMZ ===
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

    def recurse(feats):
        for feat in feats:
            if hasattr(feat, "geometry") and isinstance(feat.geometry, Polygon):
                polygons.append(feat.geometry)
            elif hasattr(feat, "features"):
                recurse(feat.features())

    recurse(k.features())

    if not polygons:
        raise Exception("No Polygon found in KML")
    
    return polygons[0]


# === Ambil Data Jalan dari OSM ===
def get_osm_roads(polygon: Polygon):
    print("🌐 Mengambil jalan dari OpenStreetMap...")
    # osmnx expects GeoSeries
    gdf_poly = gpd.GeoSeries([polygon], crs="EPSG:4326")
    roads = ox.features_from_polygon(polygon, tags={"highway": True})
    roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])]
    return roads


# === Ekspor ke DXF ===
def export_to_dxf(gdf, dxf_path):
    doc = ezdxf.new()
    msp = doc.modelspace()

    for geom in gdf.geometry:
        if geom.geom_type == "LineString":
            points = list(geom.coords)
            msp.add_lwpolyline(points)
        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                points = list(line.coords)
                msp.add_lwpolyline(points)

    doc.saveas(dxf_path)
    print(f"✅ DXF disimpan: {dxf_path}")


# === Main Flow ===
def main():
    print("📥 Membaca poligon dari KMZ...")
    polygon = extract_polygon_from_kmz(KMZ_FILE)

    print("📦 Mendownload data jalan dari OSM...")
    roads = get_osm_roads(polygon)

    print("🗺️ Proyeksi ke UTM Zone 60S...")
    roads_utm = roads.to_crs(TARGET_EPSG)

    geojson_path = os.path.join(OUTPUT_DIR, "roadmap_osm.geojson")
    roads_utm.to_file(geojson_path, driver="GeoJSON")
    print(f"✅ GeoJSON disimpan: {geojson_path}")

    dxf_path = os.path.join(OUTPUT_DIR, "roadmap_osm.dxf")
    export_to_dxf(roads_utm, dxf_path)


if __name__ == "__main__":
    main()
