import streamlit as st
import requests
import gzip
import json
import base64
import os

st.set_page_config(page_title="Auto GeoJSON Downloader", layout="wide")
st.title("🌍 Auto Downloader for Microsoft Buildings")

def auto_download(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a id="auto-download" href="data:file/geojson;base64,{b64}" download="{os.path.basename(file_path)}"></a>'
    js = "<script>document.getElementById('auto-download').click();</script>"
    st.markdown(href + js, unsafe_allow_html=True)

# Ambil parameter dari URL
params = st.experimental_get_query_params()
url = params.get("url", [None])[0]

if url:
    st.info(f"📥 Memproses file dari URL: {url}")

    # Download file CSV.GZ
    response = requests.get(url)
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
else:
    st.warning("❗ Tambahkan parameter ?url=<link> di browser untuk auto-download.")
    st.write("Contoh:")
    st.code("https://your-app-url/?url=https://minedbuildings.z5.web.core.windows.net/.../file.csv.gz")
