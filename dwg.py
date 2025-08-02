import streamlit as st
import numpy as np
import cv2
import ezdxf
import io

st.title("Deteksi Garis Jalan & Bangunan → DXF (UTM Zone 60S)")

uploaded_file = st.file_uploader("Upload Gambar (Jalan & Bangunan)", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Baca gambar
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    st.image(img, caption="Gambar Asli", use_column_width=True)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Threshold + invert
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Cari kontur untuk jalan (garis tipis)
    jalan_binary = cv2.Canny(gray, 100, 200)
    jalan_contours, _ = cv2.findContours(jalan_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Cari kontur untuk bangunan (area besar)
    bangunan_contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    st.success(f"Deteksi {len(jalan_contours)} garis jalan dan {len(bangunan_contours)} bangunan.")

    # Buat dokumen DXF
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    # UTM konversi kasar (misal 1 pixel = 0.5 meter) → atur sesuai kebutuhan
    PIXEL_SCALE = 0.5  # meter per pixel
    ORIGIN_X, ORIGIN_Y = 700000, 9250000  # koordinat UTM 60S acuan

    def pixel_to_utm(pt):
        x = ORIGIN_X + pt[0] * PIXEL_SCALE
        y = ORIGIN_Y - pt[1] * PIXEL_SCALE  # Y dibalik karena citra top-down
        return (x, y)

    # Tambahkan garis jalan ke DXF
    for cnt in jalan_contours:
        if len(cnt) < 2:
            continue
        points = [pixel_to_utm(pt[0]) for pt in cnt]
        msp.add_lwpolyline(points, dxfattribs={"layer": "JALAN"})

    # Tambahkan bangunan sebagai poligon tertutup
    for cnt in bangunan_contours:
        if len(cnt) < 3:
            continue
        points = [pixel_to_utm(pt[0]) for pt in cnt]
        msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "BANGUNAN"})

    # Simpan ke BytesIO
    dxf_buffer = io.BytesIO()
    doc.write(dxf_buffer)
    dxf_buffer.seek(0)

    # Tombol download
    st.download_button(
        label="Download DXF",
        data=dxf_buffer.getvalue(),
        file_name="output.dxf",
        mime="application/dxf"
    )
