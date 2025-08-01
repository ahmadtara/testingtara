import streamlit as st
from fastkml import kml
from shapely.geometry import Point
import ezdxf
from pyproj import Transformer
import tempfile

# Folder yang ingin diambil
TARGET_FOLDERS = [
    "EXISTING POLE EMR 7-4", "FAT", "HP COVER", "NEW POLE 7-3", "NEW POLE 7-4", "FDT"
]

# Ubah koordinat lon/lat ke UTM zona 60S (EPSG:32760)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32760", always_xy=True)

def extract_points_from_kml_file(file_obj):
    k = kml.KML()
    k.from_string(file_obj.read())
    result = []

    def recursive_extract(features, current_path=""):
        for f in features:
            name = getattr(f, 'name', '')
            new_path = f"{current_path}/{name}".upper()

            # Ambil hanya Placemark berisi titik, dan path-nya cocok
            if isinstance(f, kml.Placemark) and isinstance(f.geometry, Point):
                if any(folder in new_path for folder in TARGET_FOLDERS):
                    lon, lat = f.geometry.x, f.geometry.y
                    utm_x, utm_y = transformer.transform(lon, lat)
                    result.append((f.name or "TANPA_NAMA", utm_x, utm_y))

            # Jika masih ada nested feature
            if hasattr(f, 'features'):
                recursive_extract(f.features, new_path)

    recursive_extract(k.features)
    return result

def export_to_dxf(points, output_path):
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    for name, x, y in points:
        msp.add_point((x, y), dxfattribs={'layer': 'TITIK'})
        msp.add_text(name, dxfattribs={'height': 2.5}).set_pos((x + 2, y + 2))

    doc.saveas(output_path)

def run_kml_extraction_app():
    st.title("📍 Konversi Titik KML ke DXF (UTM Zone 60S)")

    uploaded_file = st.file_uploader("📤 Upload file .KML", type=["kml"])

    if uploaded_file:
        with st.spinner("🔍 Mengekstrak dan mengubah koordinat..."):
            try:
                points = extract_points_from_kml_file(uploaded_file)

                if not points:
                    st.warning("⚠️ Tidak ada titik ditemukan dalam folder yang ditentukan.")
                    return

                with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmpfile:
                    export_to_dxf(points, tmpfile.name)
                    st.success(f"✅ Berhasil! {len(points)} titik dikonversi ke UTM.")
                    st.download_button("⬇️ Download File DXF", data=open(tmpfile.name, "rb"), file_name="output_titik_utm60.dxf")

            except Exception as e:
                st.error(f"❌ Terjadi kesalahan saat memproses file: {e}")

if __name__ == "__main__":
    run_kml_extraction_app()
