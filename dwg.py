import streamlit as st
import cv2
import numpy as np
import ezdxf
import io
from PIL import Image
import pyproj
import pytesseract

st.title("Konversi Gambar Peta ke DXF (Jalan & Bangunan) dalam UTM Zone 60S")

uploaded_file = st.file_uploader("Upload Gambar Peta", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file).convert('RGB')
    image_np = np.array(image)

    st.image(image_np, caption="Gambar Asli", use_column_width=True)

    # --- Deteksi teks dengan OCR (pytesseract) ---
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

    mask = np.zeros_like(gray)
    n_boxes = len(data['level'])
    for i in range(n_boxes):
        (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
        cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

    # Inpaint (hapus teks)
    image_clean = cv2.inpaint(image_np, mask, 3, cv2.INPAINT_TELEA)

    st.image(image_clean, caption="Gambar Setelah Penghapusan Label (OCR)", use_column_width=True)

    # --- Deteksi garis jalan (filter horizontal & vertikal) ---
    gray_clean = cv2.cvtColor(image_clean, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray_clean, 50, 150, apertureSize=3)

    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=50, maxLineGap=10)
    road_paths = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            if abs(angle) < 10 or abs(angle) > 80:  # Hanya hampir horizontal/vertikal
                road_paths.append([(x1, y1), (x2, y2)])

    st.success(f"Deteksi {len(road_paths)} garis jalan.")

    # --- Deteksi bangunan: kontur tertutup + luas masuk akal ---
    building_paths = []
    cnts, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in cnts:
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        area = cv2.contourArea(approx)
        if area > 150 and area < 10000 and len(approx) > 3:
            poly = [(pt[0][0], pt[0][1]) for pt in approx]
            building_paths.append(poly)

    st.success(f"Deteksi {len(building_paths)} bangunan.")

    # --- Konversi koordinat ke UTM 60S ---
    h, w = image_np.shape[:2]
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32760", always_xy=True)

    def pixel_to_utm(x, y):
        lon = 130 + (x / w) * 0.01  # dummy lon
        lat = -5 - (y / h) * 0.01   # dummy lat
        return transformer.transform(lon, lat)

    # --- Buat DXF ---
    doc = ezdxf.new()
    msp = doc.modelspace()

    for path in road_paths:
        p1 = pixel_to_utm(*path[0])
        p2 = pixel_to_utm(*path[1])
        msp.add_line(p1, p2, dxfattribs={"layer": "ROAD"})

    for poly in building_paths:
        poly_utm = [pixel_to_utm(x, y) for x, y in poly]
        msp.add_lwpolyline(poly_utm, close=True, dxfattribs={"layer": "BUILDING"})

    # Simpan ke buffer teks dan encode ke bytes
    dxf_text_buffer = io.StringIO()
    doc.write(dxf_text_buffer)
    dxf_text = dxf_text_buffer.getvalue()
    dxf_data = dxf_text.encode('utf-8')

    # Tombol download
    st.download_button("Download DXF (UTM Zone 60S)", data=dxf_data, file_name="output_utm60.dxf", mime="application/dxf")
