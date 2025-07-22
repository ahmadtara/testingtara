import os
import zipfile
import geopandas as gpd
from shapely.geometry import LineString, Polygon
from fastkml import kml

# Konfigurasi
BOUNDARY_DIR = "BOUNDARY CLUSTER"
OUTPUT_DIR = "output"
TARGET_EPSG = "EPSG:32760"  # UTM Zone 60S (Indonesia Timur)

# Buat folder output jika belum ada
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_kml_from_kmz(kmz_path, extract_to):
    with zipfile.ZipFile(kmz_path, 'r') as zf:
        for f in zf.namelist():
            if f.endswith('.kml'):
                zf.extract(f, extract_to)
                return os.path.join(extract_to, f)
    return None

def extract_geometries_from_kml(kml_path):
    with open(kml_path, 'rt', encoding='utf-8') as file:
        doc = file.read()
    k = kml.KML()
    k.from_string(doc)

    placemarks = []

    def recurse_features(features):
        for f in features:
            if hasattr(f, 'geometry') and f.geometry is not None:
                placemarks.append(f)
            elif hasattr(f, 'features'):
                recurse_features(list(f.features()))

    recurse_features(list(k.features()))

    geoms = []
    for p in placemarks:
        geom = p.geometry
        # Ambil garis luar dari Polygon
        if isinstance(geom, Polygon):
            outline = geom.exterior
            geoms.append({'name': getattr(p, 'name', 'Unnamed'), 'geometry': LineString(outline.coords)})
        elif isinstance(geom, LineString):
            geoms.append({'name': getattr(p, 'name', 'Unnamed'), 'geometry': geom})

    return geoms

def convert_to_utm(geoms):
    gdf = gpd.GeoDataFrame(geoms, crs='EPSG:4326')
    return gdf.to_crs(TARGET_EPSG)

def process_all_kmz():
    for filename in os.listdir(BOUNDARY_DIR):
        if filename.endswith(".kmz"):
            print(f"⏳ Memproses: {filename}")
            base = os.path.splitext(filename)[0]
            temp_extract_path = os.path.join(BOUNDARY_DIR, "tmp")
            os.makedirs(temp_extract_path, exist_ok=True)

            kmz_path = os.path.join(BOUNDARY_DIR, filename)
            kml_path = extract_kml_from_kmz(kmz_path, temp_extract_path)

            if not kml_path:
                print(f"⚠️  Gagal extract KML dari {filename}")
                continue

            geometries = extract_geometries_from_kml(kml_path)
            if not geometries:
                print(f"⚠️  Tidak ditemukan Polygon/LineString di {filename}")
                continue

            utm_gdf = convert_to_utm(geometries)
            output_path = os.path.join(OUTPUT_DIR, f"{base}_utm.geojson")
            utm_gdf.to_file(output_path, driver='GeoJSON')
            print(f"✅ Disimpan: {output_path}")

process_all_kmz()
