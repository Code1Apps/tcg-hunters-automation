# Initialize PaddleOCR instance
from paddleocr import PaddleOCR
from pathlib import Path

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False)

# Run OCR inference on a sample image 
MODEL_PATH = "C:\\Users\\MIMI\\Dev\\Back\\tcg-hunters-automation\\public\\img\\tmp\\results\\crops\\1771162347608_hp.jpg"

result = ocr.predict(
    input=str(MODEL_PATH))

# Visualize the results and save the JSON results
for res in result:
    res.print()
    res.save_to_img("output")
    res.save_to_json("output")