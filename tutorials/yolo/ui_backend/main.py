# ui_backend/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx
import cv2
import numpy as np
from PIL import Image
import io
import base64
import os
import json
from datetime import datetime

app = FastAPI(title="Object Detection UI")

# Serve static files (optional: CSS, JS, etc.)
#app.mount("/static", StaticFiles(directory="static"), name="static")

# === CONFIG ===
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# AI Backend URL - works both in Docker and local dev
AI_BACKEND_URL = os.getenv("AI_BACKEND_URL", "http://localhost:8001")

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head>
            <title>Object Detection - YOLOv8</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f4f4f9; }
                h1 { color: #2c3e50; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
                input[type="file"] { padding: 10px; }
                input[type="submit"] { padding: 12px 30px; background: #3498db; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; }
                input[type="submit"]:hover { background: #2980b9; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Object Detection Microservice</h1>
                <p>Upload an image to detect objects using YOLOv8</p>
                <form action="/upload" enctype="multipart/form-data" method="post">
                    <input type="file" name="image" accept="image/*" required><br><br>
                    <input type="submit" value="Detect Objects">
                </form>
            </div>
        </body>
    </html>
    """

@app.post("/upload")
async def upload(image: UploadFile = File(...)):
    if not image.content_type.startswith("image/"):
        raise HTTPException(400, detail="File is not an image")

    contents = await image.read()
    filename = image.filename or "uploaded_image.jpg"

    print(f"Processing: {filename} ({len(contents)} bytes)")

    # === CALL AI BACKEND ===
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{AI_BACKEND_URL}/predict",
                files={"image": (filename, contents, image.content_type)}
            )
            resp.raise_for_status()
            results = resp.json()
    except Exception as e:
        raise HTTPException(500, detail=f"AI backend error: {str(e)}")

    # === DECODE IMAGE & DRAW BOUNDING BOXES ===
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, detail="Invalid image file")

    for det in results.get("detections", []):
        x1, y1, x2, y2 = map(int, det["bbox"])
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
        label = f"{det['class']} {det['confidence']:.2f}"
        cv2.putText(img, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    # === SAVE RESULTS ===
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    base_name = f"{timestamp}_{os.path.splitext(filename)[0].replace(' ', '_')}"
    output_img_path = os.path.join(OUTPUT_DIR, f"{base_name}_result.jpg")
    output_json_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")

    cv2.imwrite(output_img_path, img)
    print(f"Image saved: {output_img_path}")

    json_data = {
        "original_filename": filename,
        "processed_at": datetime.now().isoformat(),
        "output_image": os.path.basename(output_img_path),
        "detections": results.get("detections", [])
    }
    with open(output_json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"JSON saved: {output_json_path}")

    # === RETURN IMAGE AS BASE64 FOR BROWSER ===
    _, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    img_b64 = base64.b64encode(buffer).decode()

    return {
        "status": "success",
        "message": f"Detected {len(results.get('detections', []))} objects",
        "image_result": f"data:image/jpeg;base64,{img_b64}",
        "saved_image": os.path.basename(output_img_path),
        "saved_json": os.path.basename(output_json_path),
        "detections": results.get("detections", [])
    }