DeepSeek-OCR

deepseek-ocr  : 

HF : https://huggingface.co/deepseek-ai/DeepSeek-OCR

GitHub : 
https://github.com/deepseek-ai/DeepSeek-OCR/

- Steps
```bash
git clone https://github.com/deepseek-ai/DeepSeek-OCR.git

python3.10 -m venv venv
source venv/bin/activate
wget https://github.com/vllm-project/vllm/releases/download/v0.8.5/vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl


pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu118
pip install vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl
pip install -r requirements.txt
pip install flash-attn==2.7.3 --no-build-isolation
```

vllm infernce

```bash
cd DeepSeek-OCR-master/DeepSeek-OCR-vllm
python run_dpsk_ocr_image.py
```