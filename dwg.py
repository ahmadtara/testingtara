import os
from fastkml import kml
from shapely.geometry import Point
from pyproj import Transformer
import ezdxf

# Folder target yang ingin diambil
target_folders = {
    'FDT',
    'NEW POLE 7-3',
    'NEW POLE 7-4',
    'EXISTING POLE EMR 7-4',
    'FAT',
    'HP COVER'
}

# Fungsi untuk parsing KML dan ambil titik dari folder tertentu
def extract_points_from_kml(kml_path):
    with open(kml_path, 'r', encoding='utf-8') as f:
        kml_content = f.read()

    k = kml.KML()
    k.from_string(kml_content)

    extracted_points = []

    def extract_features(features, current_folder=None):
        for feature in features:
            name = getattr(feature, 'name', '')
            if hasattr(feature, 'geometry') and isinstance(feature.geometry, Point):
                if current_folder in target_folders:
                    coords = (feature.geometry.x, feature.geometry.y)
                    extracted_points.append((current_folder, name, coords))
            elif hasattr(feature, 'features') and callable(feature.features):
                sub_features = list(feature.features())
                extract_features(sub_features, name)

    root_features = list(k.features())
    extract_features(root_features)

    return extracted_points

# Fungsi konversi ke UTM Zona 60S
def to_utm60(lon, lat):
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32760", always_xy=True)
    x, y = transformer.transform(lon, lat)
    return x, y

# Simpan hasil ke DXF
def save_to_dxf(data, output_path='output.dxf'):
    doc = ezdxf.new()
    msp = doc.modelspace()
    for folder, name, (lon, lat) in data:
        x, y = to_utm60(lon, lat)
        msp.add_point((x, y))
        msp.add_text(
            f"{name}",
            dxfattribs={"height": 2.5}
        ).set_pos((x + 2, y + 2))
    doc.saveas(output_path)
    print(f"DXF saved: {output_path}")

# Jalankan
if __name__ == '__main__':
    input_kml = "contoh.kml"  # Ganti sesuai nama file
    if not os.path.exists(input_kml):
        print(f"File tidak ditemukan: {input_kml}")
    else:
        titik = extract_points_from_kml(input_kml)
        if not titik:
            print("⚠️ Tidak ada titik ditemukan dari folder yang ditentukan.")
        else:
            for f, n, (lon, lat) in titik:
                print(f"[{f}] {n}: ({lon}, {lat})")
            save_to_dxf(titik, "hasil_output_utm60.dxf")
