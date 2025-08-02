import streamlit as st
import cv2
import numpy as np
import ezdxf
from io import BytesIO

# Transform pixel ke UTM
def pixel_to_utm(x_px, y_px, ref_x_px, ref_y_px, ref_easting, ref_northing, scale):
    easting = ref_easting + (x_px - ref_x_px) * scale
    northing = ref_northing - (y_px - ref_y_px) * scale
    return (easting, northing)

def detect_lines(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80, minLineLength=30, maxLineGap=5)
    return lines

def detect_buildings(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours

def create_dxf(lines, polygons, ref, scale):
    ref_x_px, ref_y_px, ref_e, ref_n = ref

    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()

    # Tambah garis jalan
    if lines is not None:
        for l in lines:
            x1, y1, x2, y2 = l[0]
            p1 = pixel_to_utm(x1,y1,ref_x_px,ref_y_px,ref_e,ref_n,scale)
            p2 = pixel_to_utm(x2,y2,ref_x_px,ref_y_px,ref_e,ref_n,scale)
            msp.add_line(p1,p2,dxfattribs={"layer":"Jalan"})

    # Tambah poligon bangunan
    for c in polygons:
        pts = [pixel_to_utm(pt[0][0], pt[0][1], ref_x_px, ref_y_px, ref_e, ref_n, scale) for pt in c]
        if len(pts)>=3:
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer":"Bangunan"})

    return doc

# Streamlit UI
st.title("Konversi Gambar Peta ke DXF (Koordinat UTM Zone 60S)")

uploaded_file = st.file_uploader("Upload gambar peta (PNG/JPG)...", type=["png","jpg","jpeg"])

st.subheader("Titik Referensi Koordinat UTM")
col1, col2 = st.columns(2)
with col1:
    ref_x_px = st.number_input("Pixel X", value=1000)
    ref_e = st.number_input("Easting (meter)", value=500000.0)
with col2:
    ref_y_px = st.number_input("Pixel Y", value=500)
    ref_n = st.number_input("Northing (meter)", value=10000000.0)

scale = st.number_input("Skala (meter per pixel)", min_value=0.01, max_value=10.0, value=0.5)

if uploaded_file is not None:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, 1)

    st.image(image, caption="Gambar Input", use_column_width=True)

    lines = detect_lines(image)
    polygons = detect_buildings(image)

    st.success(f"Deteksi {0 if lines is None else len(lines)} garis jalan dan {len(polygons)} bangunan.")

    doc = create_dxf(lines, polygons, (ref_x_px, ref_y_px, ref_e, ref_n), scale)

    dxf_bytes = BytesIO()
    doc.write(dxf_bytes)
    dxf_bytes.seek(0)

    st.download_button(
        label="Download DXF",
        data=dxf_bytes,
        file_name="output_utm60.dxf",
        mime="application/dxf"
    )
