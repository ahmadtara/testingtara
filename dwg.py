
import streamlit as st
from predict import detect_and_export
import os

st.title("Deteksi Rumah dari Gambar Peta (Detectron2)")
uploaded_file = st.file_uploader("Upload gambar peta", type=["jpg", "png", "jpeg"])

if uploaded_file:
    with open("input.jpg", "wb") as f:
        f.write(uploaded_file.read())
    st.image("input.jpg", caption="Gambar Diupload", use_column_width=True)

    output_path = detect_and_export("input.jpg")
    st.success("Deteksi selesai, hasil DXF siap diunduh.")
    with open(output_path, "rb") as f:
        st.download_button("Download DXF", f, file_name="output.dxf")
