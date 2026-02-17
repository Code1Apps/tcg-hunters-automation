import onnxruntime as ort
import os
import json

model_path = r"c:\Users\MIMI\Dev\Back\tcg-hunters-automation\src\weights\pokemon-resolver-key-dataset.onnx"

if not os.path.exists(model_path):
    print(f"Model not found at {model_path}")
else:
    try:
        session = ort.InferenceSession(model_path)
        meta = session.get_modelmeta().custom_metadata_map
        if 'names' in meta:
            names = meta['names']
            print(f"NAMES_JSON: {names}")
        else:
            print("No 'names' found in metadata")
        
        for output in session.get_outputs():
             print(f"Output Shape: {output.shape}")
             
    except Exception as e:
        print(f"Error: {e}")
