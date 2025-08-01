import streamlit as st
from fastkml import kml
import ezdxf
from shapely.geometry import Point
from pyproj import Transformer
import tempfile

def extract_points_from_kml_file(kml_content):
    k = kml.KML()
    k.from_string(kml_content)

    points = []

    def recurse_features(features):
        for feature in features:
            if hasattr(feature, 'geometry') and isinstance(feature.geometry, Point):
                name = getattr(feature, 'name', 'TANPA_NAMA')
                coords = (feature.geometry.x, feature.geometry.y)
                points.append((name, coords))
            if hasattr(feature, 'features'):
                recurse_features(feature.features())

    recurse_features(k.features())
    return points

def convert_to_dxf(points, output_path):
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Konversi koordinat dari WGS84 ke UTM zona 60N
    transformer = Transformer.from_crs("epsg:4326", "epsg:32660", always_xy=True)

    for name, (lon, lat) in points:
        x, y = transformer.transform(lon, lat)
        msp.add_circle((x, y), radius=1.0)
        msp.add_text(name, dxfattribs={"height": 1.5}).set_pos((x + 2, y + 2))

    doc.saveas(output_path)

# Streamlit App
st.title("Konversi Titik KML ke DXF (UTM Zona 60)")

uploaded_file = st.file_uploader("Unggah File KML", type=["kml"])
if uploaded_file is not None:
    try:
        content = uploaded_file.read().decode("utf-8")
        points = extract_points_from_kml_file(content)

        if points:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp_dxf:
                convert_to_dxf(points, tmp_dxf.name)
                st.success("✅ Berhasil dikonversi ke DXF.")
                st.download_button("⬇️ Unduh DXF", data=open(tmp_dxf.name, "rb"), file_name="hasil_konversi.dxf")
        else:
            st.warning("⚠️ Tidak ada titik ditemukan dalam file KML.")
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses file: {e}")
