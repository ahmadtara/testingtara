# dwg.py
import streamlit as st
import os
import tempfile
from convert_kml import process_kml_to_dxf

st.set_page_config(page_title="KML to DXF Road Extractor", layout="centered")
st.title("🗺️ KML → DXF Road Converter")

uploaded_file = st.file_uploader("Upload file .KML (area batas cluster)", type=["kml"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as tmp:
        tmp.write(uploaded_file.read())
        kml_path = tmp.name

    output_dir = "output"
    st.info("🔄 Memproses file...")

    try:
        dxf_path, geojson_path, jalan_ditemukan = process_kml_to_dxf(kml_path, output_dir)
        st.success("✅ Jalan berhasil ditemukan dan diproses!")

        with open(dxf_path, "rb") as f:
            st.download_button("⬇️ Download DXF", f, file_name="roadmap_osm.dxf")
        with open(geojson_path, "rb") as f:
            st.download_button("⬇️ Download GeoJSON", f, file_name="roadmap_osm.geojson")

    except Exception as e:
        st.error(f"❌ Terjadi kesalahan: {e}")
