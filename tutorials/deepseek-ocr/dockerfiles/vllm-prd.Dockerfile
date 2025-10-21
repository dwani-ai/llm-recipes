# Builder stage: Install dependencies and build
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04 AS builder

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including Python 3.10
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git wget curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3 as default
RUN ln -s /usr/bin/python3 /usr/bin/python

# Upgrade pip
RUN pip install --upgrade pip

# Install PyTorch and related packages with CUDA 11.8 support
RUN pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu118

# Install vLLM directly from the wheel URL
RUN pip install https://github.com/vllm-project/vllm/releases/download/v0.8.5/vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl

# Install flash-attn without build isolation
RUN pip install flash-attn==2.7.3 --no-build-isolation

# Runtime stage: Minimal image for deployment
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install minimal system dependencies including Python 3.10
RUN apt-get update && apt-get install -y \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3 as default
RUN ln -s /usr/bin/python3 /usr/bin/python

# Create working directory
WORKDIR /app

# Copy Python site-packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy requirements.txt (if needed for future use)
COPY requirements.txt .

# Expose port for vLLM OpenAI-compatible API server (default port 8000)
EXPOSE 8000

# Default command to run vLLM OpenAI API server (customize --model as needed)
CMD ["python", "-m", "vllm.entrypoints.openai.api_server", "--host", "0.0.0.0", "--port", "8000"]