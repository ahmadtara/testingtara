
import cv2
import ezdxf
import torch
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2 import model_zoo
import numpy as np

def detect_and_export(image_path):
    cfg = get_cfg()
    cfg.merge_from_file("detectron2_config.yaml")
    cfg.MODEL.WEIGHTS = "model_final.pth"
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
    predictor = DefaultPredictor(cfg)

    img = cv2.imread(image_path)
    outputs = predictor(img)
    instances = outputs["instances"].to("cpu")

    doc = ezdxf.new()
    msp = doc.modelspace()

    for mask in instances.pred_masks:
        contours, _ = cv2.findContours(mask.numpy().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            points = [(int(p[0][0]), -int(p[0][1])) for p in cnt]
            if len(points) >= 3:
                msp.add_lwpolyline(points, close=True)

    output_dxf = "output.dxf"
    doc.saveas(output_dxf)
    return output_dxf
