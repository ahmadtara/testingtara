import streamlit as st
from fastkml import kml
from shapely.geometry import Point
import ezdxf
import os

TARGET_FOLDERS = [
    "EXISTING POLE EMR 7-4", "FAT", "HP COVER", "NEW POLE 7-3", "NEW POLE 7-4", "FDT"
]


def extract_points_from_kml_file(file_obj):
    k = kml.KML()
    k.from_string(file_obj.read())
    result = []

    def extract_features(features, current_path=""):
        for f in features:
            if isinstance(f, kml.Placemark) and isinstance(f.geometry, Point):
                if any(folder in current_path.upper() for folder in TARGET_FOLDERS):
                    result.append((f.name, f.geometry.x, f.geometry.y))
            elif hasattr(f, 'features'):
                new_path = f"{current_path}/{f.name}" if hasattr(f, 'name') else current_path
                extract_features(f.features, new_path)

    extract_features(k.features)
    return result


def export_to_dxf(points, output_path):
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    for name, lon, lat in points:
        x, y = lon, lat  # Ubah ke UTM jika dibutuhkan
        msp.add_point((x, y), dxfattribs={'layer': 'TITIK'})
        msp.add_text(name, dxfattribs={'height': 2.5}).set_pos((x + 0.00005, y + 0.00005))

    doc.saveas(output_path)


def run_kml_extraction_app():
    st.title("📍 Extract Titik PO dari KML dan Konversi ke DXF")

    uploaded_file = st.file_uploader("📤 Upload file .KML", type=["kml"])

    if uploaded_file:
        with st.spinner("🔍 Mengekstrak titik..."):
            try:
                points = extract_points_from_kml_file(uploaded_file)

                if not points:
                    st.warning("⚠️ Tidak ada titik ditemukan dalam folder yang ditentukan.")
                    return

                output_path = "/tmp/output_titik.dxf"
                export_to_dxf(points, output_path)

                st.success(f"✅ Berhasil! Ditemukan {len(points)} titik.")
                with open(output_path, "rb") as f:
                    st.download_button("⬇️ Download File DXF", data=f, file_name="output_titik.dxf")

            except Exception as e:
                st.error(f"❌ Terjadi kesalahan saat memproses file: {e}")


if __name__ == "__main__":
    run_kml_extraction_app()
