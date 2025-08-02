import cv2
import numpy as np
import ezdxf
from ultralytics import YOLO
from PIL import Image

# Load YOLOv8 model
model = YOLO('yolov8-building.pt')  # Pastikan file ini sudah kamu upload

# Load image dari Google Maps
image_path = "maps.jpg"  # Ganti nama jika file berbeda
img = cv2.imread(image_path)
height, width = img.shape[:2]

# Deteksi dengan YOLOv8
results = model(img)

# Ambil hasil bounding box dari YOLO
boxes = results[0].boxes.xyxy.cpu().numpy()  # (x1, y1, x2, y2)

# Buat DXF baru
doc = ezdxf.new()
msp = doc.modelspace()

# Gambar deteksi ke DXF
for box in boxes:
    x1, y1, x2, y2 = box
    # Skala dan offset: 1 pixel = 1 unit, letakkan ke 0,0
    # Konversi ke polyline rectangle (agar rapi)
    points = [
        (x1, -y1),  # Y dibalik karena gambar = top-down
        (x2, -y1),
        (x2, -y2),
        (x1, -y2),
        (x1, -y1),  # Tutup kembali
    ]
    msp.add_lwpolyline(points, close=True)

# Simpan ke DXF
doc.saveas("output_buildings.dxf")
print("DXF saved: output_buildings.dxf")
