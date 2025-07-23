import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
import requests
import os
import zipfile

st.title("🌍 Global ML Building Footprints Downloader")
st.caption("Convert Microsoft building footprints to GeoJSON for any country")

# Pilihan negara
countries = ["Indonesia", "Greece", "Angola", "India"]
selected_country = st.selectbox("Pilih Negara", countries)

if st.button("🔽 Download & Convert"):
    st.info(f"Proses untuk {selected_country} dimulai...")

    # Ambil daftar dataset
    links_url = "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"
    dataset_links = pd.read_csv(links_url)
    country_links = dataset_links[dataset_links.Location == selected_country]

    if country_links.empty:
        st.error("Dataset tidak ditemukan!")
    else:
        os.makedirs("output", exist_ok=True)
        all_files = []

        for _, row in country_links.iterrows():
            st.write(f"📥 Download {row.Url}")
            # Baca file GeoJSONL
            df = pd.read_json(row.Url, lines=True)
            df['geometry'] = df['geometry'].apply(shape)
            gdf = gpd.GeoDataFrame(df, crs=4326)

            out_file = f"output/{row.QuadKey}.geojson"
            gdf.to_file(out_file, driver="GeoJSON")
            all_files.append(out_file)

        # Gabungkan ke ZIP
        zip_path = f"{selected_country}_buildings.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in all_files:
                zipf.write(file)

        st.success(f"✅ Proses selesai! {len(all_files)} file dibuat.")
        with open(zip_path, "rb") as f:
            st.download_button("⬇️ Download ZIP", f, file_name=zip_path)
