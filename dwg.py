import streamlit as st
import os
from convert_kmz import process_kmz_to_dxf

st.title("Konversi KMZ ke DXF dengan Data Jalan OSM")

uploaded_file = st.file_uploader("Unggah file .KMZ", type=["kmz"])

if uploaded_file is not None:
    kmz_path = os.path.join("BOUNDARY CLUSTER", uploaded_file.name)
    with open(kmz_path, "wb") as f:
        f.write(uploaded_file.read())
    
    with st.spinner("Memproses file..."):
        try:
            dxf_path, geojson_path = process_kmz_to_dxf(kmz_path, "output")
            st.success("✅ Berhasil dikonversi!")

            with open(dxf_path, "rb") as f:
                st.download_button("⬇️ Download DXF", f, file_name="roadmap_osm.dxf")
            with open(geojson_path, "rb") as f:
                st.download_button("⬇️ Download GeoJSON", f, file_name="roadmap_osm.geojson")

        except Exception as e:
            st.error(f"❌ Terjadi kesalahan: {e}")
