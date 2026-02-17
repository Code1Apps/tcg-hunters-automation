import onnxruntime as ort
import os

model_path = r"c:\Users\MIMI\Dev\Back\tcg-hunters-automation\src\weights\pokemon-resolver-key-dataset.onnx"

if not os.path.exists(model_path):
    print(f"Model not found at {model_path}")
else:
    try:
        session = ort.InferenceSession(model_path)
        for input in session.get_inputs():
            print(f"Input Name: {input.name}, Shape: {input.shape}")
    except Exception as e:
        print(f"Error: {e}")
