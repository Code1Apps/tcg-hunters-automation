import argparse
import os
import json
import time
from pathlib import Path
import cv2
from paddleocr import PaddleOCR

# --- Configuration ---
MODEL = "PP-OCRv5"

# Initialize OCR for CPU
ocr = PaddleOCR(
    ocr_version=MODEL,
    use_angle_cls=True,
    lang='en',
    enable_mkldnn=True,     # SIGNIFICANT speed boost for Intel Xeon
    cpu_threads=4           # Match your physical cores
)

def sort_results(ocr_results):
    """
    Sorts OCR results from top-left to bottom-right.
    ocr_results format: [[box], (text, score)]
    """
    if not ocr_results:
        return []
    
    # Simple sort: Y-first, then X
    # For more complex layouts, grouping by lines would be better,
    # but top-left to bottom-right is usually interpreted as Y-major.
    # We'll use a tolerance for Y to handle slightly tilted text lines.
    
    # Sort by Y coordinate
    sorted_by_y = sorted(ocr_results, key=lambda x: x[0][0][1])
    
    if not sorted_by_y:
        return []

    # Better line grouping: Use average height to determine if words are on the same line
    heights = [abs(res[0][2][1] - res[0][0][1]) for res in sorted_by_y]
    avg_height = sum(heights) / len(heights) if heights else 10
    line_threshold = avg_height * 0.5
    
    lines = []
    if sorted_by_y:
        current_line = [sorted_by_y[0]]
        for i in range(1, len(sorted_by_y)):
            if abs(sorted_by_y[i][0][0][1] - current_line[0][0][0][1]) < line_threshold:
                current_line.append(sorted_by_y[i])
            else:
                # Sort the current line by X coordinate
                current_line.sort(key=lambda x: x[0][0][0])
                lines.extend(current_line)
                current_line = [sorted_by_y[i]]
        
        # Last line
        current_line.sort(key=lambda x: x[0][0][0])
        lines.extend(current_line)

    return [line[1][0] for line in lines]

def main():
    parser = argparse.ArgumentParser(description="OCR processing for TCG Images (CPU MODE)")
    parser.add_argument("--folder", type=str, default="public/img/tmp", help="Folder to process")
    args = parser.parse_args()
    
    root_dir = Path(__file__).resolve().parent.parent
    target_dir = root_dir / args.folder
    
    if not target_dir.exists():
        print(f"❌ Directory not found: {target_dir}")
        return

    # Support common image formats
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
    image_files = [f for f in target_dir.iterdir() if f.suffix.lower() in valid_extensions]
    
    if not image_files:
        print(f"❓ No images found in {target_dir}")
        return

    print(f"🚀 Found {len(image_files)} images to process in {args.folder}")

    processed_count = 0
    start_time = time.time()

    for img_p in image_files:
        try:
            # Load and process image
            # PaddleOCR.ocr returns a list of results (one per image if not batch)
            # result[0] is the list of lines for the image
            result = ocr.ocr(str(img_p), cls=True)
            
            if not result or not result[0]:
                print(f"⚠️ [{processed_count+1}/{len(image_files)}] No text found in {img_p.name}")
                texts = []
            else:
                # Sort and extract text
                texts = sort_results(result[0])
                print(f"✅ [{processed_count+1}/{len(image_files)}] Processed {img_p.name} - found {len(texts)} text blocks")

            # Save to JSON file with same name
            json_p = img_p.with_suffix(".json")
            with open(json_p, "w", encoding="utf-8") as f:
                json.dump({"texts": texts}, f, indent=4, ensure_ascii=False)
            
        except Exception as e:
            print(f"❌ Error processing {img_p.name}: {e}")

        processed_count += 1

    elapsed = time.time() - start_time
    print(f"🏁 DONE — Processed {processed_count} images in {elapsed:.2f}s")

if __name__ == "__main__":
    main()
