from fastkml import kml
from shapely.geometry import Point
import ezdxf

TARGET_FOLDERS = {
    "EXISTING POLE EMR 7-4", "FAT", "HP COVER", "NEW POLE 7-3", "NEW POLE 7-4", "FDT"
}

def extract_points_from_kml(kml_path):
    with open(kml_path, 'r', encoding='utf-8') as f:
        doc = f.read()

    k = kml.KML()
    k.from_string(doc.encode('utf-8'))

    result = []

    def extract_features(features, current_path=""):
        for f in features:
            if isinstance(f, kml.Placemark) and isinstance(f.geometry, Point):
                if any(folder in current_path.upper() for folder in TARGET_FOLDERS):
                    result.append((f.name, f.geometry.x, f.geometry.y))
            elif hasattr(f, 'features'):
                new_path = f"{current_path}/{f.name}" if hasattr(f, 'name') else current_path
                extract_features(f.features(), new_path)

    extract_features(k.features())
    return result

def save_to_dxf(points, output_path):
    doc = ezdxf.new()
    msp = doc.modelspace()
    for name, lon, lat in points:
        msp.add_point((lon, lat))
        msp.add_text(name, dxfattribs={"height": 1}).set_pos((lon + 0.0001, lat + 0.0001))
    doc.saveas(output_path)

# Jalankan fungsi
kml_file = "SRI MERANTI RW 16 PEKANBARU.kml"  # ganti dengan path jika beda
output_dxf = "output_pole_points.dxf"

points = extract_points_from_kml(kml_file)
save_to_dxf(points, output_dxf)

print(f"Sukses menyimpan {len(points)} titik ke dalam file DXF.")
