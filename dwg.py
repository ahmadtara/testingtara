import streamlit as st
import cv2
import numpy as np
import ezdxf
import io
from PIL import Image
import pyproj

st.title("Ekstraksi Garis Bangunan dari Gambar Google Maps (UTM Zone 60S)")

uploaded_file = st.file_uploader("Upload Gambar Google Maps", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file).convert('RGB')
    image_np = np.array(image)
    st.image(image_np, caption="Gambar Asli", use_column_width=True)

    # --- Deteksi bangunan ---
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, 50, 150)

    # Morph untuk menutup celah
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)
    closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    building_paths = []
    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)
        area = cv2.contourArea(approx)
        if area > 100 and len(approx) >= 4:
            poly = [(pt[0][0], pt[0][1]) for pt in approx]
            building_paths.append(poly)

    st.success(f"Deteksi {len(building_paths)} bangunan.")

    # --- Georeferencing ---
    geo_ref = [
        (0, 0, 130.0000, -5.0000),
        (image_np.shape[1], image_np.shape[0], 130.0100, -5.0100)
    ]

    (x1, y1, lon1, lat1), (x2, y2, lon2, lat2) = geo_ref

    def pixel_to_lonlat(x, y):
        lon = lon1 + (x - x1) / (x2 - x1) * (lon2 - lon1)
        lat = lat1 + (y - y1) / (y2 - y1) * (lat2 - lat1)
        return lon, lat

    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32760", always_xy=True)

    def pixel_to_utm(x, y):
        lon, lat = pixel_to_lonlat(x, y)
        return transformer.transform(lon, lat)

    origin_utm_x, origin_utm_y = pixel_to_utm(0, 0)

    def pixel_to_utm_shifted(x, y):
        utm_x, utm_y = pixel_to_utm(x, y)
        return utm_x - origin_utm_x, utm_y - origin_utm_y

    # --- Buat DXF ---
    doc = ezdxf.new()
    msp = doc.modelspace()

    for poly in building_paths:
        poly_utm = [pixel_to_utm_shifted(x, y) for x, y in poly]
        msp.add_lwpolyline(poly_utm, close=True, dxfattribs={"layer": "BUILDING"})

    dxf_text_buffer = io.StringIO()
    doc.write(dxf_text_buffer)
    dxf_text = dxf_text_buffer.getvalue()
    dxf_data = dxf_text.encode('utf-8')

    st.download_button("Download DXF Bangunan (UTM Zone 60S)", data=dxf_data, file_name="building_only_utm60.dxf", mime="application/dxf")
