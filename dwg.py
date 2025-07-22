import streamlit as st
from convert_kmz import process_kmz_to_dxf
import tempfile
import os

st.set_page_config(page_title="KMZ to DXF Road Extractor", layout="centered")
st.title("🚧 KMZ → DXF Peta Jalan (OpenStreetMap)")

uploaded_file = st.file_uploader("Unggah file .KMZ batas wilayah", type=["kmz"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kmz") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    st.success("✅ File KMZ berhasil diunggah!")

    if st.button("🚀 Proses dan Unduh"):
        with st.spinner("⏳ Memproses file dan mengambil data jalan..."):
            try:
                output_dir = tempfile.mkdtemp()
                dxf_path, geojson_path = process_kmz_to_dxf(tmp_path, output_dir)

                st.success("✅ Selesai! Unduh hasilnya di bawah ini:")

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
