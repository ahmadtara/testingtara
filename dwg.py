# app.py
import os
import streamlit as st
from convert_kmz import process_kmz_to_dxf

st.title("🗺️ Konversi KMZ ke DXF Jalan (OpenStreetMap)")

uploaded_file = st.file_uploader("Unggah file KMZ", type=["kmz"])

if uploaded_file is not None:
    kmz_path = os.path.join("BOUNDARY CLUSTER", uploaded_file.name)
    os.makedirs(os.path.dirname(kmz_path), exist_ok=True)

    with open(kmz_path, "wb") as f:
        f.write(uploaded_file.read())

    st.success("✅ File berhasil diunggah. Memproses...")

    try:
        dxf_path, geojson_path = process_kmz_to_dxf(kmz_path)
        st.success("✅ Konversi berhasil!")

        with open(dxf_path, "rb") as f:
            st.download_button("⬇️ Download DXF", f, file_name="roadmap_osm.dxf")

        with open(geojson_path, "rb") as f:
            st.download_button("⬇️ Download GeoJSON", f, file_name="roadmap_osm.geojson")

    except Exception as e:
        st.error(f"❌ Terjadi kesalahan: {e}")
