import shutil
import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Form, WebSocket
from pydantic import BaseModel
import asyncio
import json

# Import from existing codebase
# We need to make sure the path is correct. 
# Since api.py is in the same dir as rag-main.py, we can import directly if we are careful with sys.path or just rely on relative imports if it was a package.
# But rag-main is a script. Let's try to import from it.
# However, rag-main is not a module name that is standard (hyphen).
# I might need to rename rag-main.py to rag_main.py or use importlib.
# Or I can just duplicate the minimal logic needed or refactor rag-main.py.
# Refactoring rag-main.py to rag_main.py is safer for importing.

import importlib.util
spec = importlib.util.spec_from_file_location("rag_main", "rag-main.py")
rag_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rag_main)

# Now we can use rag_main.process_pdf, rag_main.Config, etc.
process_pdf = rag_main.process_pdf
Config = rag_main.Config
resolve_pdf_path = rag_main.resolve_pdf_path
download_google_drive_file = rag_main.download_google_drive_file
is_url = rag_main.is_url
from modules.splitter_metadata import check_qdrant_existence

app = FastAPI(title="MedChat RAG Pipeline API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PipelineRequest(BaseModel):
    url: Optional[str] = None
    p1: bool = True
    p2: bool = True
    p3: bool = True
    clean: bool = False

@app.get("/")
def read_root():
    return {"message": "MedChat RAG Pipeline API is running"}

@app.get("/status")
def get_status(limit: int = 50):
    """Get the last N lines from the pipeline log."""
    log_file = Config.PIPELINE_ROOT / "logs" / "pipeline_status.log"
    if not log_file.exists():
        return {"logs": []}
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return {"logs": [line.strip() for line in lines[-limit:]]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {str(e)}"]}

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# --- Patch Pipeline Logger for WebSocket ---
pipeline_logger_instance = rag_main.pipeline_logger
running_loop = None

@app.on_event("startup")
async def startup_event():
    global running_loop
    running_loop = asyncio.get_running_loop()

def broadcast_log(phase, status, details=""):
    step_map = {"Split": 1, "OCR": 2, "Embedding": 3}
    base_phase = phase.split(" ")[0] if " " in phase else phase
    step = step_map.get(base_phase, 0)
    
    # Map status to UI expected status
    status_lower = status.lower()
    if status_lower == "started": ui_status = "processing"
    elif status_lower == "completed": ui_status = "completed"
    elif status_lower == "skipped": ui_status = "skipped"
    elif status_lower == "error": ui_status = "error"
    else: ui_status = "processing"

    msg = {
        "step": step,
        "status": ui_status,
        "message": f"[{phase}] {status}: {details}"
    }
    
    if running_loop and manager:
        asyncio.run_coroutine_threadsafe(manager.broadcast(msg), running_loop)

# Apply Patch
original_log_phase = pipeline_logger_instance.log_phase
def patched_log_phase(phase, status, details=""):
    broadcast_log(phase, status, details)
    original_log_phase(phase, status, details)

pipeline_logger_instance.log_phase = patched_log_phase

def run_pipeline_task(file_path: Path, phases: dict):
    try:
        # Notify Start
        if running_loop and manager:
             asyncio.run_coroutine_threadsafe(manager.broadcast({"step": 0, "status": "initializing", "message": f"Starting pipeline for {file_path.name}"}), running_loop)
             
        process_pdf(file_path, phases)
        
        # Notify Finish (if not already by logger)
        if running_loop and manager:
             asyncio.run_coroutine_threadsafe(manager.broadcast({"step": 4, "status": "completed", "message": "Pipeline Finished"}), running_loop)

    except Exception as e:
        print(f"Error in background task: {e}")
        if running_loop and manager:
             asyncio.run_coroutine_threadsafe(manager.broadcast({"step": 0, "status": "error", "message": str(e)}), running_loop)

@app.post("/process")
async def process_document(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    p1: bool = Form(True),
    p2: bool = Form(True),
    p3: bool = Form(True),
    clean: bool = Form(False),
    check_only: bool = Form(False),
    overwrite: bool = Form(False)
):
    print(f"DEBUG: /process called with p1={p1}, overwrite={overwrite}")
    if not file and not url:
        raise HTTPException(status_code=400, detail="Either file or url must be provided")

    target_path = None
    
    # Ensure RAW_DIR exists
    Config.RAW_DIR.mkdir(parents=True, exist_ok=True)

    if file:
        target_path = Config.RAW_DIR / file.filename
        with target_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    elif url:
        # Handle URL logic similar to rag-main.py
        if "drive.google.com" in url:
             try:
                 path_str = download_google_drive_file(url, output_dir=str(Config.RAW_DIR))
                 target_path = Path(path_str)
             except Exception as e:
                 raise HTTPException(status_code=400, detail=f"Failed to download from GDrive: {e}")
        else:
            try:
                path_str = resolve_pdf_path(url, download_dir=str(Config.RAW_DIR))
                target_path = Path(path_str)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to download URL: {e}")

    if not target_path or not target_path.exists():
         raise HTTPException(status_code=500, detail="Failed to process input file")

    # If check_only is True, check for existing split files and return status
    if check_only:
        # Logic from rag-main.py get_split_files
        # We need to check for each file if it's a directory
        results = []
        files_to_check = []
        if target_path.is_dir():
            files_to_check = list(target_path.glob("*.pdf"))
        else:
            files_to_check = [target_path]
            
        for pdf_file in files_to_check:
            # Check for existing split files
            existing_split = list(Config.SPLITTED_DIR.glob(f"{pdf_file.stem}(*-*).pdf"))
            
            # Check Qdrant
            q_check = check_qdrant_existence(pdf_file)
            
            results.append({
                "filename": pdf_file.name,
                "exists_local": len(existing_split) > 0,
                "exists_qdrant": q_check.get("exists", False),
                "qdrant_count": q_check.get("count", 0),
                "exists": len(existing_split) > 0 or q_check.get("exists", False),
                "count": max(len(existing_split), q_check.get("count", 0))
            })
            
        return {"status": "checked", "results": results}

    # If target_path is a directory (e.g. from GDrive folder), we need to iterate
    files_to_process = []
    if target_path.is_dir():
        files_to_process = list(target_path.glob("*.pdf"))
    else:
        files_to_process = [target_path]

    phases = {'p1': p1, 'p2': p2, 'p3': p3, 'clean': clean, 'overwrite': overwrite}
    print(f"DEBUG: api.py constructed phases: {phases}")
    
    for pdf_file in files_to_process:
        background_tasks.add_task(run_pipeline_task, pdf_file, phases)

    return {
        "message": "Pipeline started", 
        "files": [f.name for f in files_to_process],
        "phases": phases
    }

# --- Mock Logic for UI Testing ---

EXISTING_FILES_MOCK = ["machine_learning_101.pdf", "medical_handbook.pdf"]



@app.websocket("/ws/pipeline")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)

async def run_mock_pipeline_task(filename: str, overwrite: bool):
    """Giả lập pipeline chạy"""
    action_msg = "Overwriting existing data..." if overwrite else "Processing new file..."
    
    await manager.broadcast({"step": 0, "status": "initializing", "message": f"Setup: {action_msg}"})
    await asyncio.sleep(1)

    steps = [
        {"step": 1, "status": "splitting", "message": "Phase 1: Smart Splitting & Metadata"},
        {"step": 2, "status": "ocr", "message": "Phase 2: Mistral OCR & Translation"},
        {"step": 3, "status": "indexing", "message": "Phase 3: Embedding & Qdrant Indexing"},
    ]

    for step in steps:
        await manager.broadcast(step)
        await asyncio.sleep(2)

    await manager.broadcast({"step": 4, "status": "completed", "message": "Done."})

class MockPipelineRequest(BaseModel):
    filename: str
    overwrite: bool = False

@app.post("/check-file")
async def check_file_existence(file: UploadFile = File(...)):
    """
    Bước 1: Kiểm tra xem file đã tồn tại trong DB chưa.
    Trả về true/false để Frontend quyết định có hiện Popup không.
    """
    # Logic thực tế: Tính hash của file và check trong DB
    is_exists = file.filename in EXISTING_FILES_MOCK
    
    return {
        "filename": file.filename,
        "exists": is_exists
    }

@app.post("/start-rag")
async def start_rag_process_mock(req: MockPipelineRequest, background_tasks: BackgroundTasks):
    """
    Bước 2: Kích hoạt pipeline sau khi đã quyết định Overwrite hay không.
    """
    background_tasks.add_task(run_mock_pipeline_task, req.filename, req.overwrite)
    return {"status": "started", "filename": req.filename, "overwrite": req.overwrite}
