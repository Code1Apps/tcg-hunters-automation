import os
import cv2
import json
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from paddleocr import PaddleOCR

# --- 1. CONFIGURATION & MODELS ---
# Replace with your actual .onnx path exported from YOLO11 OBB
MODEL_PATH = Path(__file__).resolve().parent / "weights" / "pokemon_resolver_key_dataset_s.onnx"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = PROJECT_ROOT / "public" / "img" / "tmp"
OUTPUT_DIR = IMAGE_DIR
DEBUG_CROPS = False
CROP_DIR = OUTPUT_DIR / "crops"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CROP_DIR.mkdir(parents=True, exist_ok=True)

# Initialize YOLO (HBB Detection)
model = YOLO(MODEL_PATH)

# Initialize PaddleOCR (CPU mode with angle classifier)
ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False
)

# --- 2. MAIN LOOP ---
def main():
    image_files = list(IMAGE_DIR.glob("*.jpg"))
    print(f"🚀 Found {len(image_files)} images. Starting batch processing...")

    for img_p in image_files:
        try:
            img = cv2.imread(str(img_p))
            if img is None: continue

            # Run YOLO11 Inference
            results = model.predict(img, conf=0.7)
            
            card_results = {
                "filename": img_p.name,
                "hp": None,
                "amount": [],
                "attack_count": 0
            }

            for r in results:
                # HBB outputs: [x1, y1, x2, y2]
                if r.boxes is None: continue
                boxes = r.boxes.xyxy.cpu().numpy()
                classes = r.boxes.cls.cpu().numpy()
                names = r.names

                # Collect and sort detections by Y-coordinate (top to bottom)
                detections = []
                for box, cls_idx in zip(boxes, classes):
                    detections.append({
                        "box": box,
                        "cls_idx": cls_idx,
                        "label": names[int(cls_idx)].lower()
                    })
                
                # Sort by y1 (index 1 of box)
                detections.sort(key=lambda x: x["box"][1])

                amt_count = 0
                for det in detections:
                    label = det["label"]
                    box = det["box"]
                    
                    if label == "attack":
                        card_results["attack_count"] += 1
                    elif label in ["hp", "amount"]:
                        x1, y1, x2, y2 = map(int, box)
                        
                        # 1. Standard Crop
                        crop = img[y1:y2, x1:x2]
                        if crop.size == 0: continue

                        # 2. Preprocess: Add padding + scaling
                        pad = 5
                        crop = cv2.copyMakeBorder(crop, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
                        crop = cv2.resize(crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

                        # Save crop
                        if label == "hp":
                            crop_name = f"{img_p.stem}_hp.jpg"
                        else:
                            crop_name = f"{img_p.stem}_amount_{amt_count}.jpg"
                            amt_count += 1
                        
                        if DEBUG_CROPS:
                            cv2.imwrite(str(CROP_DIR / crop_name), crop)

                        # 3. Run OCR
                        predictions = list(ocr.predict([crop]))
                        if not predictions: continue
                        
                        res = getattr(predictions[0], 'res', predictions[0].json.get('res', {}))
                        if 'rec_texts' in res:
                            raw_text = "".join(res['rec_texts']).strip()
                            # Replace special characters as requested
                            clean_text = raw_text.replace('×', 'x').replace('−', '-')
                            
                            if label == "hp":
                                # Keep only digits for HP
                                card_results["hp"] = "".join([c for c in clean_text if c.isdigit()])
                            else:
                                if clean_text: card_results["amount"].append(clean_text)
            
            # Save individual result to JSON
            json_path = OUTPUT_DIR / f"{img_p.stem}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(card_results, f, indent=4)

            print(f"✅ Processed {img_p.name}: HP={card_results['hp']}, AMTS={card_results['amount']}, ATTACKS={card_results['attack_count']}")

        except Exception as e:
            print(f"❌ Error processing {img_p.name}: {e}")

if __name__ == "__main__":
    main()
