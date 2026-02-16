import argparse
import time
import json
import os
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import cv2
from paddleocr import PaddleOCR
import onnxruntime as ort

# --- Configuration ---
BATCH_SIZE = 8
OCR_MODEL = "PP-OCRv5"
ONNX_MODEL_PATH = str(Path(__file__).resolve().parent / "weights" / "pokemon-resolver-key-dataset.onnx")
CONF_THRESHOLD = 0.25
NMS_THRESHOLD = 0.45
IMG_SIZE = 1024

# Class mapping from model metadata
CLASSES = {0: 'hp', 1: 'amount', 2: 'attack'}

# Initialize OCR for CPU
ocr = PaddleOCR(
    ocr_version=OCR_MODEL,
    use_angle_cls=True,
    text_recognition_batch_size=BATCH_SIZE,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    lang='en',
    enable_mkldnn=False,
    cpu_threads=4,
)

# Initialize ONNX session
session = ort.InferenceSession(ONNX_MODEL_PATH)
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

def letterbox(img, new_shape=(IMG_SIZE, IMG_SIZE), color=(114, 114, 114)):
    # Resize and pad image while meeting stride-multiple constraints
    shape = img.shape[:2]  # current shape [height, width]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # Scale ratio (new / old)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])

    # Compute padding
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding

    dw /= 2  # divide padding into 2 sides
    dh /= 2

    if shape[::-1] != new_unpad:  # resize
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # add border
    return img, r, (dw, dh)

def nms(boxes, scores, iou_threshold):
    # Standard NMS
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)

        inds = np.where(ovr <= iou_threshold)[0]
        order = order[inds + 1]

    return keep

def detect_regions(img):
    # Preprocess
    img_padded, ratio, (dw, dh) = letterbox(img)
    blob = img_padded.transpose(2, 0, 1)  # HWC to CHW
    blob = blob[np.newaxis, :, :, :].astype(np.float32) / 255.0  # Add batch dim and normalize

    # Inference
    outputs = session.run([output_name], {input_name: blob})[0]
    outputs = np.squeeze(outputs).T  # [n_boxes, 7]

    # Postprocess
    boxes = outputs[:, :4]  # cx, cy, w, h
    scores = outputs[:, 4:]  # class scores
    
    # cx, cy, w, h -> x1, y1, x2, y2
    x1 = boxes[:, 0] - boxes[:, 2] / 2
    y1 = boxes[:, 1] - boxes[:, 3] / 2
    x2 = boxes[:, 0] + boxes[:, 2] / 2
    y2 = boxes[:, 1] + boxes[:, 3] / 2
    boxes = np.stack([x1, y1, x2, y2], axis=1)

    all_detections = []
    for i in range(len(CLASSES)):
        class_scores = scores[:, i]
        mask = class_scores > CONF_THRESHOLD
        class_boxes = boxes[mask]
        class_scores = class_scores[mask]
        
        if len(class_scores) > 0:
            keep = nms(class_boxes, class_scores, NMS_THRESHOLD)
            for idx in keep:
                # Rescale boxes to original image
                box = class_boxes[idx]
                box[[0, 2]] -= dw
                box[[1, 3]] -= dh
                box /= ratio
                # Clip boxes to image boundaries
                box[[0, 2]] = np.clip(box[[0, 2]], 0, img.shape[1])
                box[[1, 3]] = np.clip(box[[1, 3]], 0, img.shape[0])
                
                all_detections.append({
                    'class': CLASSES[i],
                    'box': box.astype(int).tolist(),
                    'score': float(class_scores[keep]) if isinstance(class_scores[keep], float) else float(class_scores[idx])
                })
    return all_detections

def debug_draw(img, detections, output_path):
    # Draw detections on image for debugging
    debug_img = img.copy()
    for det in detections:
        box = det['box']
        label = det['class']
        score = det['score']
        
        # Color based on class
        color = (0, 255, 0) if label == 'attack' else (255, 0, 0) if label == 'hp' else (0, 165, 255)
        
        cv2.rectangle(debug_img, (box[0], box[1]), (box[2], box[3]), color, 2)
        cv2.putText(debug_img, f"{label} {score:.2f}", (box[0], box[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    cv2.imwrite(str(output_path), debug_img)

def save_json(json_path, data):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="OCR JPG → JSON with Region Detection")
    parser.add_argument("folder", type=str, nargs='?', default="public/img/tmp", help="Folder containing jpg files")
    parser.add_argument("--debug", action="store_true", default=True, help="Save debug images with detections")
    args = parser.parse_args()

    base_path = Path(args.folder).resolve()
    if not base_path.exists():
        print("❌ Folder does not exist")
        return

    jpg_files = list(base_path.glob("**/*.jpg"))
    # Filter out previous debug images if any
    jpg_files = [f for f in jpg_files if "_debug" not in f.stem]
    
    if not jpg_files:
        print("❓ No JPG files found")
        return

    print(f"🚀 Found {len(jpg_files)} JPG files")
    start_time = time.time()
    processed = 0

    with ThreadPoolExecutor(max_workers=2) as pool:
        for img_path in jpg_files:
            json_path = img_path.with_suffix(".json")
            if json_path.exists():
                continue

            img = cv2.imread(str(img_path))
            if img is None:
                print(f"⚠️ Could not read {img_path}")
                continue

            try:
                # 1. Detect regions using ONNX model
                detections = detect_regions(img)
                
                # 2. Debug: Save detection image
                if args.debug:
                    debug_path = img_path.parent / f"{img_path.stem}_debug.jpg"
                    debug_draw(img, detections, debug_path)

                # 3. Process detections
                result_data = {
                    "hp": None,
                    "amount": [],
                    "attack_count": 0
                }

                # Sort detections from top to bottom, then left to right
                # Key: (y_min, x_min)
                sorted_detections = sorted(detections, key=lambda d: (d['box'][1], d['box'][0]))

                for det in sorted_detections:
                    label = det['class']
                    box = det['box']
                    
                    if label == 'attack':
                        result_data["attack_count"] += 1
                    elif label in ['hp', 'amount']:
                        # Crop and OCR
                        crop = img[box[1]:box[3], box[0]:box[2]]
                        if crop.size > 0:
                            # Use PaddleOCR only on the crop
                            ocr_res = ocr.predict([crop])[0]
                            text = " ".join(ocr_res.json.get("res", {}).get("rec_texts", [])).strip()
                            if label == 'hp':
                                if result_data["hp"] is None:
                                    result_data["hp"] = text
                                else:
                                    result_data["hp"] += " " + text
                            else:
                                result_data["amount"].append(text)

                pool.submit(save_json, json_path, result_data)

                processed += 1
                elapsed = time.time() - start_time
                speed = processed / elapsed if elapsed > 0 else 0
                print(f"✅ Processed: {img_path.name} | Speed: {speed:.2f} img/sec")

            except Exception as e:
                print(f"❌ Error on {img_path}: {e}")

    print(f"🏁 DONE — {processed} new files processed in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    main()
