# ai_backend/Dockerfile
FROM python:3.11-slim

# Minimal system libs for OpenCV (no bloat)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install base requirements first (for layer caching)
COPY requirements_ai.txt .
RUN pip install --no-cache-dir -r requirements_ai.txt

# Install ultralytics + opencv last (latest compatible versions)
RUN pip install --no-cache-dir \
    ultralytics \
    opencv-python-headless

RUN pip install python-multipart

COPY main.py .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]