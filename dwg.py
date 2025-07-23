import streamlit as st
import pandas as pd
import requests
import gzip
import json
import base64
import os

st.set_page_config(page_title="Auto GeoJSON Downloader", layout="wide")
st.title("🌍 Auto Downloader from Local CSV")

def auto_download(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a id="auto-download" href="data:file/geojson;base64,{b64}" download="{os.path.basename(file_path)}"></a>'
    js = "<script>document.getElementById('auto-download').click();</script>"
    st.markdown(href + js, unsafe_allow_html=True)

# Upload CSV lokal
csv_file = st.file_uploader("Upload CSV yang berisi daftar URL", type=["csv"])

if csv_file:
    df = pd.read_csv(csv_file)
    st.success(f"✅ CSV berhasil dimuat! {len(df)} baris ditemukan.")

    # Pilih kolom URL
    url_column = st.selectbox("Pilih kolom URL", df.columns.tolist())
    selected_url = st.selectbox("Pilih URL untuk diproses", df[url_column].tolist())

    # Proses otomatis setelah user pilih URL
    if selected_url:
        st.info(f"📥 Memproses file: {selected_url}")
        
        # Download file CSV.GZ
        response = requests.get(selected_url)
        temp_file = "temp.csv.gz"
        with open(temp_file, "wb") as f:
            f.write(response.content)

        # Extract & convert to GeoJSON
        features = []
        with gzip.open(temp_file, "rt", encoding="utf-8") as gz:
            for line in gz:
                try:
                    feature = json.loads(line.strip())
                    features.append(feature)
                except:
                    continue

        geojson = {"type": "FeatureCollection", "features": features}
        output_file = "buildings.geojson"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(geojson, f)

        st.success(f"✅ Konversi selesai! {len(features)} fitur berhasil diproses.")
        st.write("💡 Download otomatis dimulai...")
        auto_download(output_file)
