text
YOLO - API server


### **Step 1: Setup Virtual Environment**

Terminal 1 → AI Backend

- cd ai_backend
- python -m venv venv_ai
- .\venv_ai\Scripts\Activate.ps1
- pip install -r requirements_ai.txt

Terminal 2 → UI Backend

- cd ..\ui_backend
- python -m venv venv_ui
- .\venv_ui\Scripts\Activate.ps1
- pip install -r requirements.txt


### **Step 2: Run Services**

Terminal 1:
- uvicorn main:app --host 0.0.0.0 --port 8001 --reload

Terminal 2:
- uvicorn main:app --host 0.0.0.0 --port 8000 --reload


### **Step 3: Test**

    Open: http://localhost:8000

    Upload image ✅

    Check: output/ folder


-- With Docker

- Docker start with image build
    docker compose up --build -d

- Docker start for subsequent runs
    docker compose up -d