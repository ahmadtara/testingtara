# app.py
import streamlit as st
from convert_kmz import process_kmz_to_dxf
import tempfile
import os

st.set_page_config(page_title="Konversi KMZ ke DXF", layout="centered")

st.title("📍 Konversi KMZ ke DXF Peta Jalan")
st.markdown("""
Unggah file `.kmz` yang berisi batas wilayah (polygon). 
Aplikasi akan mengambil data jalan dari OpenStreetMap (OSM) dan mengonversi ke format DXF & GeoJSON.
""")

uploaded_file = st.file_uploader("📤 Unggah file KMZ", type=["kmz"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kmz") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    st.success("✅ File KMZ berhasil diunggah!")

    if st.button("🚀 Proses KMZ"):
        with st.spinner("⏳ Memproses..."):
            try:
                output_dir = tempfile.mkdtemp()
                dxf_path, geojson_path = process_kmz_to_dxf(tmp_path, output_dir)

                st.success("✅ Berhasil dikonversi!")

                with open(dxf_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Unduh DXF",
                        data=f,
                        file_name="roadmap_osm.dxf",
                        mime="application/dxf"
                    )

                with open(geojson_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Unduh GeoJSON",
                        data=f,
                        file_name="roadmap_osm.geojson",
                        mime="application/geo+json"
                    )

            except Exception as e:
                st.error(f"❌ Terjadi kesalahan: {e}")
