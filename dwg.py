import streamlit as st
from PIL import Image
import numpy as np
import ezdxf
import io
import pyproj
from ultralytics import YOLO

st.title("Deteksi Bangunan dari Gambar Google Maps dengan YOLOv8")

uploaded_file = st.file_uploader("Upload Gambar Peta (Google Maps)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file).convert('RGB')
    image_np = np.array(image)
    st.image(image_np, caption="Gambar Asli", use_column_width=True)

    # --- Load YOLOv8 model ---
    model = YOLO("yolov8-building.pt")  # Ganti dengan path model kamu
    results = model(image_np)

    boxes = results[0].boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
    st.success(f"Terdeteksi {len(boxes)} bangunan.")

    # --- Georeferencing sederhana (ubah sesuai lokasi kamu) ---
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

    for box in boxes:
        x_min, y_min, x_max, y_max = box
        corners_px = [
            (x_min, y_min),
            (x_max, y_min),
            (x_max, y_max),
            (x_min, y_max)
        ]
        corners_utm = [pixel_to_utm_shifted(x, y) for x, y in corners_px]
        msp.add_lwpolyline(corners_utm, close=True, dxfattribs={"layer": "BUILDING"})

    # Save as DXF
    buffer = io.StringIO()
    doc.write(buffer)
    dxf_data = buffer.getvalue().encode("utf-8")

    st.download_button("Download DXF Bangunan (YOLOv8)", data=dxf_data, file_name="buildings_yolo.dxf", mime="application/dxf")
