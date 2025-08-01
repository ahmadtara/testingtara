import streamlit as st
from fastkml import kml
from shapely.geometry import Point
import ezdxf
import os
from io import BytesIO

# Folder-folder yang akan diambil titiknya
TARGET_FOLDERS = {
    "EXISTING POLE EMR 7-4", "FAT", "HP COVER", "NEW POLE 7-3", "NEW POLE 7-4", "FDT"
}

def extract_points_from_kml_file(file_obj):
    """Baca dan ekstrak titik dari file KML (upload-an)"""
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
                extract_features(f.features(), new_path)

    extract_features(k.features())
    return result

def save_points_to_dxf(points):
    """Simpan titik-titik ke dalam file DXF di memori"""
    doc = ezdxf.new()
    msp = doc.modelspace()
    for name, lon, lat in points:
        msp.add_point((lon, lat))
        msp.add_text(name, dxfattribs={"height": 1}).set_pos((lon + 0.0001, lat + 0.0001))
    
    # Simpan ke memori
    dxf_bytes = BytesIO()
    doc.write(dxf_bytes)
    dxf_bytes.seek(0)
    return dxf_bytes

# ==== Streamlit App ====
st.title("📌 Konversi Titik KML → DXF (Folder Tertentu Saja)")

uploaded_file = st.file_uploader("📂 Upload file KML", type=["kml"])

if uploaded_file is not None:
    try:
        points = extract_points_from_kml_file(uploaded_file)

        if not points:
            st.warning("🚫 Tidak ditemukan titik dari folder yang ditentukan.")
        else:
            st.success(f"✅ Ditemukan {len(points)} titik yang valid.")

            dxf_file = save_points_to_dxf(points)

            st.download_button(
                label="⬇️ Download File DXF",
                data=dxf_file,
                file_name="output_titik.dxf",
                mime="application/dxf"
            )
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses file: {e}")
else:
    st.info("Silakan upload file KML terlebih dahulu.")
