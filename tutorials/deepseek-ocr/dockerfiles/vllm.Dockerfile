# Use NVIDIA CUDA base image for CUDA 11.8 support
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including Python 3.10 (compatible with cp38 abi3 wheel)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git wget curl\
    && rm -rf /var/lib/apt/lists/*

# Set Python 3 as default
RUN ln -s /usr/bin/python3 /usr/bin/python

# Create working directory
WORKDIR /app

# Copy requirements.txt and the vLLM wheel file (assumes these are in the build context)
COPY requirements.txt .
RUN wget https://github.com/vllm-project/vllm/releases/download/v0.8.5/vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl
#COPY vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl .

# Upgrade pip
RUN pip install --upgrade pip

# Install PyTorch and related packages with CUDA 11.8 support
RUN pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu118

# Install vLLM from the local wheel
RUN pip install vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl

# Install dependencies from requirements.txt
#RUN pip install -r requirements.txt

# Install flash-attn without build isolation
RUN pip install flash-attn==2.7.3 --no-build-isolation

# Expose port for vLLM OpenAI-compatible API server (default port 8000)
EXPOSE 8000

# Default command to run vLLM OpenAI API server (customize --model as needed)
CMD ["python", "-m", "vllm.entrypoints.openai.api_server", "--host", "0.0.0.0", "--port", "8000"]