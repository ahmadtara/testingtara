import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
import os
import zipfile
import base64

st.set_page_config(page_title="Global ML Building Downloader", layout="wide")
st.title("🌍 Global ML Building Footprints Downloader")
st.caption("Download & Convert Microsoft building footprints to GeoJSON")

# --- Fungsi Auto-Download ---
def auto_download(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a id="auto-download" href="data:file/zip;base64,{b64}" download="{os.path.basename(file_path)}"></a>'
    js = """
    <script>
    document.getElementById('auto-download').click();
    </script>
    """
    st.markdown(href + js, unsafe_allow_html=True)

# Pilihan negara
countries = ["Indonesia", "Greece", "Angola", "India"]
selected_country = st.selectbox("Pilih Negara", countries)

if st.button("🔽 Download & Convert"):
    st.info(f"Proses download dan konversi untuk {selected_country} dimulai...")

    # Ambil daftar dataset dari Microsoft
    links_url = "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"
    dataset_links = pd.read_csv(links_url)
    country_links = dataset_links[dataset_links.Location == selected_country]

    if country_links.empty:
        st.error("Dataset tidak ditemukan!")
    else:
        os.makedirs("output", exist_ok=True)
        all_files = []

        for _, row in country_links.iterrows():
            st.write(f"📥 Mengunduh {row.Url}")
            # Download dan baca GeoJSONL
            df = pd.read_json(row.Url, lines=True)
            df['geometry'] = df['geometry'].apply(shape)
            gdf = gpd.GeoDataFrame(df, crs=4326)

            # Simpan sebagai GeoJSON
            out_file = f"output/{row.QuadKey}.geojson"
            gdf.to_file(out_file, driver="GeoJSON")
            all_files.append(out_file)

        # Buat file ZIP
        zip_path = f"{selected_country}_buildings.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in all_files:
                zipf.write(file)

        st.success(f"✅ Proses selesai! {len(all_files)} file dibuat.")

        # Tombol download dan auto-download
        with open(zip_path, "rb") as f:
            st.download_button("⬇️ Download ZIP", f, file_name=os.path.basename(zip_path))

        st.info("💡 Download otomatis dimulai...")
        auto_download(zip_path)
