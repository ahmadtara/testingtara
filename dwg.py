import tkinter as tk
from tkinter import filedialog, messagebox
from fastkml import kml
from pyproj import Transformer
import ezdxf
import os

# Target folder yang diambil
target_folders = {'FDT', 'NEW POLE 7-3', 'NEW POLE 7-4', 'EXISTING POLE EMR 7-4', 'FAT', 'HP COVER'}
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32760", always_xy=True)  # WGS84 ke UTM zona 60S

def parse_kml(file_path):
    with open(file_path, 'rt', encoding='utf-8') as f:
        doc = f.read()
    k = kml.KML()
    k.from_string(doc)

    result = []

    def extract_features(features):
        for f in features:
            if hasattr(f, 'features'):
                fname = f.name
                if fname in target_folders:
                    for placemark in f.features():
                        if hasattr(placemark, 'geometry') and placemark.geometry.geom_type == 'Point':
                            lon, lat = placemark.geometry.x, placemark.geometry.y
                            easting, northing = transformer.transform(lon, lat)
                            result.append({
                                'folder': fname,
                                'placemark': placemark.name,
                                'easting': round(easting, 3),
                                'northing': round(northing, 3)
                            })
                extract_features(f.features())
    extract_features(k.features())
    return result

def generate_dxf(data, output_path):
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()
    for item in data:
        x, y = item['easting'], item['northing']
        label = f"{item['placemark']}\n({item['folder']})"
        msp.add_point((x, y))
        msp.add_text(label, dxfattribs={'height': 2.5}).set_pos((x, y + 3), align='CENTER')
    doc.saveas(output_path)

def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("KML files", "*.kml")])
    if file_path:
        try:
            data = parse_kml(file_path)
            output_name = os.path.splitext(os.path.basename(file_path))[0] + "_output.dxf"
            output_path = os.path.join(os.path.dirname(file_path), output_name)
            generate_dxf(data, output_path)
            messagebox.showinfo("Berhasil", f"✅ File DXF berhasil dibuat:\n{output_path}")
        except Exception as e:
            messagebox.showerror("Gagal", f"❌ Terjadi kesalahan:\n{e}")

# GUI
root = tk.Tk()
root.title("KML ➜ DXF Converter (UTM 60S)")
root.geometry("400x200")

label = tk.Label(root, text="Klik tombol di bawah untuk memilih file .kml", font=("Arial", 12))
label.pack(pady=30)

btn = tk.Button(root, text="Upload KML dan Convert ke DXF", command=select_file, font=("Arial", 11), bg="green", fg="white")
btn.pack()

root.mainloop()
