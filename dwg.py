import os
from fastkml import kml
from shapely.geometry import Point
import ezdxf
import pyproj

# Folder target (huruf kapital)
TARGET_FOLDERS = ['FDT', 'NEW POLE 7-3', 'NEW POLE 7-4', 'EXISTING POLE EMR 7-4', 'FAT', 'HP COVER']

# Proyeksi ke UTM zona 60S
wgs84 = pyproj.CRS("EPSG:4326")
utm60 = pyproj.CRS("EPSG:32760")
project = pyproj.Transformer.from_crs(wgs84, utm60, always_xy=True).transform

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

def convert_to_dxf(points, output_path="output.dxf"):
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()

    for name, lon, lat, folder in points:
        x, y = project(lon, lat)
        msp.add_circle((x, y), radius=0.5)
        msp.add_text(name, dxfattribs={'height': 2.5}).set_pos((x, y + 1), align='CENTER')

    doc.saveas(output_path)
    print(f"✅ File berhasil diekspor ke {output_path}")

if __name__ == "__main__":
    file_path = "SRI MERANTI RW 16 PEKANBARU.kml"  # Ganti jika nama beda
    titik = extract_points_from_kml_file(file_path)

    if titik:
        convert_to_dxf(titik, "hasil_output.dxf")
    else:
        print("⚠️ Tidak ada titik ditemukan dalam folder yang ditentukan.")
