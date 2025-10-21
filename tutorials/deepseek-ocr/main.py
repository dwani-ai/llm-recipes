from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import torch
import os
import tempfile
import shutil
from transformers import AutoModel, AutoTokenizer
import uvicorn

# Set environment for GPU
os.environ["CUDA_VISIBLE_DEVICES"] = '0'

# Model configuration
model_name = 'deepseek-ai/DeepSeek-OCR'
prompt = "<image>\n<|grounding|>Convert the document to markdown. "

# Load tokenizer and model once at startup
print("Loading tokenizer and model...")
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModel.from_pretrained(model_name, _attn_implementation='flash_attention_2', trust_remote_code=True, use_safetensors=True)
model = model.eval().cuda().to(torch.bfloat16)
print("Model loaded successfully.")

app = FastAPI(title="DeepSeek OCR API", description="API for document-to-markdown conversion using DeepSeek-OCR")

@app.post("/ocr", summary="Extract markdown from uploaded image")
async def ocr_image(file: UploadFile = File(..., description="Image file (e.g., JPG, PNG)")):
    """
    Upload an image file and receive the extracted markdown text.
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Save uploaded file temporarily
    image_path = None
    temp_output_dir = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            image_path = tmp_file.name
        
        # Create temporary output directory
        temp_output_dir = tempfile.mkdtemp()
        
        # Run inference with save_results=True to get processed markdown
        res = model.infer(
            tokenizer, 
            prompt=prompt, 
            image_file=image_path, 
            output_path=temp_output_dir,  # Valid temp dir to avoid path errors
            base_size=1024, 
            image_size=640, 
            crop_mode=True, 
            save_results=True,  # Enable to process and save markdown
            test_compress=True
        )
        
        # Read the saved markdown file
        result_file = os.path.join(temp_output_dir, 'result.mmd')
        if os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                markdown_text = f.read().strip()
        else:
            # Fallback to returned res if no file saved
            markdown_text = str(res).strip()
        
        return JSONResponse(content={"markdown": markdown_text})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")
    
    finally:
        # Clean up temp image file
        if image_path and os.path.exists(image_path):
            os.unlink(image_path)
        # Clean up temp output dir if created
        if temp_output_dir and os.path.exists(temp_output_dir):
            shutil.rmtree(temp_output_dir)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)