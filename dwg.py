import sys
import os
from fastkml import kml
from pyproj import Transformer
import ezdxf

# Folder yang ingin diambil
target_folders = {
    'FDT',
    'NEW POLE 7-3',
    'NEW POLE 7-4',
    'EXISTING POLE EMR 7-4',
    'FAT',
    'HP COVER'
}

# Transformer: WGS84 ke UTM zona 60S
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32760", always_xy=True)

def parse_kml(kml_path):
    with open(kml_path, 'rt', encoding='utf-8') as f:
        doc = f.read()

    k = kml.KML()
    k.from_string(doc)

    points = []

    def extract(features):
        for f in features:
            if hasattr(f, 'features'):
                fname = f.name.strip() if f.name else ""
                if fname in target_folders:
                    for placemark in f.features():
                        if hasattr(placemark, 'geometry') and placemark.geometry.geom_type == 'Point':
                            lon, lat = placemark.geometry.x, placemark.geometry.y
                            easting, northing = transformer.transform(lon, lat)
                            points.append({
                                'folder': fname,
                                'placemark': placemark.name,
                                'easting': round(easting, 3),
                                'northing': round(northing, 3)
                            })
                extract(f.features())
    extract(k.features())
    return points

def generate_dxf(data, output_path):
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()

    for item in data:
        x, y = item['easting'], item['northing']
        label = f"{item['placemark']}\n({item['folder']})"
        msp.add_point((x, y))
        msp.add_text(label, dxfattribs={'height': 2.5}).set_pos((x, y + 3), align='CENTER')

    doc.saveas(output_path)
    print(f"✅ DXF berhasil disimpan di: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ Gunakan format: python convert_kml_to_dxf.py file.kml")
        sys.exit(1)

    input_kml = sys.argv[1]
    if not os.path.exists(input_kml):
        print(f"❌ File tidak ditemukan: {input_kml}")
        sys.exit(1)

    data = parse_kml(input_kml)

    if not data:
        print("⚠️ Tidak ditemukan placemark dalam folder target.")
        sys.exit(0)

    # Output file
    output_dxf = os.path.splitext(input_kml)[0] + "_output.dxf"
    generate_dxf(data, output_dxf)
