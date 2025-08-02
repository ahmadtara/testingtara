import streamlit as st
import cv2
import numpy as np
import ezdxf
import io
from PIL import Image
import pyproj

st.title("Konversi Gambar Peta ke DXF (Jalan & Bangunan) dalam UTM Zone 60S")

uploaded_file = st.file_uploader("Upload Gambar Peta", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file).convert('RGB')
    image_np = np.array(image)

    st.image(image_np, caption="Gambar Asli", use_column_width=True)

    # --- Deteksi garis jalan (dengan skeleton agar rapi) ---
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)

    # Skeleton agar garis tunggal
    skel = np.zeros(edges.shape, np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    done = False
    temp = np.copy(edges)
    while not done:
        eroded = cv2.erode(temp, element)
        temp_dilated = cv2.dilate(eroded, element)
        temp_subtracted = cv2.subtract(temp, temp_dilated)
        skel = cv2.bitwise_or(skel, temp_subtracted)
        temp = eroded.copy()
        done = cv2.countNonZero(temp) == 0

    lines = cv2.HoughLinesP(skel, 1, np.pi / 180, threshold=80, minLineLength=40, maxLineGap=5)
    road_paths = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            road_paths.append([(x1, y1), (x2, y2)])

    st.success(f"Deteksi {len(road_paths)} garis jalan.")

    # --- Deteksi bangunan: kontur tertutup + filter luas ---
    building_paths = []
    cnts, _ = cv2.findContours(skel, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in cnts:
        approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)
        area = cv2.contourArea(approx)
        if area > 100 and area < 50000 and len(approx) >= 3:
            poly = [(pt[0][0], pt[0][1]) for pt in approx]
            building_paths.append(poly)

    st.success(f"Deteksi {len(building_paths)} bangunan.")

    # --- Georeferencing: pixel -> lonlat -> UTM ---
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

    # --- Offset agar semua objek start di (0, 0) ---
    origin_utm_x, origin_utm_y = pixel_to_utm(0, 0)
    def pixel_to_utm_shifted(x, y):
        utm_x, utm_y = pixel_to_utm(x, y)
        return utm_x - origin_utm_x, utm_y - origin_utm_y

    # --- Buat DXF ---
    doc = ezdxf.new()
    msp = doc.modelspace()

    for path in road_paths:
        p1 = pixel_to_utm_shifted(*path[0])
        p2 = pixel_to_utm_shifted(*path[1])
        msp.add_line(p1, p2, dxfattribs={"layer": "ROAD"})

    for poly in building_paths:
        poly_utm = [pixel_to_utm_shifted(x, y) for x, y in poly]
        msp.add_lwpolyline(poly_utm, close=True, dxfattribs={"layer": "BUILDING"})

    # Simpan ke buffer teks dan encode ke bytes
    dxf_text_buffer = io.StringIO()
    doc.write(dxf_text_buffer)
    dxf_text = dxf_text_buffer.getvalue()
    dxf_data = dxf_text.encode('utf-8')

    # Tombol download
    st.download_button("Download DXF (UTM Zone 60S, Origin di 0,0)", data=dxf_data, file_name="output_utm60.dxf", mime="application/dxf")
