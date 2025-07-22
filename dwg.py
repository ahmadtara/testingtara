# app.py
import streamlit as st
import os
import tempfile
from convert_kmz import process_kmz_to_dxf

st.set_page_config(page_title="KMZ to DXF Road Extractor", layout="centered")
st.title("🗺️ KMZ → DXF Road Converter")

uploaded_file = st.file_uploader("Upload file .KMZ (area batas cluster)", type=["kmz"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kmz") as tmp:
        tmp.write(uploaded_file.read())
        kmz_path = tmp.name

    output_dir = "output"
    st.info("🔄 Memproses file...")

    try:
        dxf_path, geojson_path = process_kmz_to_dxf(kmz_path, output_dir)
        st.success("✅ Sukses diproses!")
        with open(dxf_path, "rb") as f:
            st.download_button("⬇️ Download DXF", f, file_name="roadmap_osm.dxf")
        with open(geojson_path, "rb") as f:
            st.download_button("⬇️ Download GeoJSON", f, file_name="roadmap_osm.geojson")
    except Exception as e:
        st.error(f"❌ Terjadi kesalahan: {e}")
