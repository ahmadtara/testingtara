import os
from fastkml import kml
from shapely.geometry import Point
import ezdxf
import pyproj

# Folder target yang harus dicari di path
TARGET_FOLDERS = ['FDT', 'NEW POLE 7-3', 'NEW POLE 7-4', 'EXISTING POLE EMR 7-4', 'FAT', 'HP COVER']

# Proyeksi koordinat dari WGS84 ke UTM zona 60S
wgs84 = pyproj.CRS("EPSG:4326")
utm60 = pyproj.CRS("EPSG:32760")  # UTM Zone 60S
project = pyproj.Transformer.from_crs(wgs84, utm60, always_xy=True).transform

# Fungsi untuk mencari file .kml terbaru di /mnt/data/
def find_latest_kml(folder="/mnt/data"):
    kml_files = [f for f in os.listdir(folder) if f.lower().endswith(".kml")]
    if not kml_files:
        return None
    kml_files.sort(key=lambda x: os.path.getmtime(os.path.join(folder, x)), reverse=True)
    return os.path.join(folder, kml_files[0])

def extract_points_from_kml_file(kml_path):
    with open(kml_path, 'r', encoding='utf-8') as f:
        doc = f.read()

    k = kml.KML()
    k.from_string(doc)

    result = []

    def extract_features(features, current_path=""):
        for f in features:
            folder_path = f"{current_path}/{getattr(f, 'name', '')}".upper()
            if isinstance(f, kml.Placemark) and isinstance(f.geometry, Point):
                if any(folder in folder_path for folder in TARGET_FOLDERS):
                    result.append((f.name, f.geometry.x, f.geometry.y, folder_path))
            elif hasattr(f, 'features'):
                extract_features(f.features(), folder_path)

    extract_features(k.features())
    return result

def convert_to_dxf(points, output_path="/mnt/data/hasil_output.dxf"):
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()

    for name, lon, lat, folder in points:
        x, y = project(lon, lat)
        msp.add_circle((x, y), radius=0.5)
        msp.add_text(name or "TANPA NAMA", dxfattribs={'height': 2.5}).set_pos((x, y + 1), align='CENTER')

    doc.saveas(output_path)
    print(f"✅ DXF berhasil disimpan: {output_path}")

# Jalankan program utama
if __name__ == "__main__":
    file_path = find_latest_kml()
    if not file_path:
        print("❌ Tidak ada file .kml ditemukan di folder /mnt/data")
    else:
        print(f"📄 Memproses file: {file_path}")
        titik = extract_points_from_kml_file(file_path)

        if titik:
            convert_to_dxf(titik)
        else:
            print("⚠️ Tidak ada titik ditemukan dalam folder yang ditentukan.")
