import shutil
import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Form, WebSocket
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
import asyncio
import json

import rag_main

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

@app.get("/library")
def get_library():
    """Fetch list of indexed books from Qdrant by scanning all points."""
    try:
        client = QdrantClient(url=Config.QDRANT_URL, port=443, api_key=Config.QDRANT_API_KEY)
        
        if not client.collection_exists(Config.COLLECTION_NAME):
             return {"books": [], "stats": {"keyword_distribution": {}, "language_distribution": {}, "avg_chunk_length": 0}}

        books_map = {}
        keyword_counts = {"disease": 0, "symptom": 0, "treatment": 0, "drug": 0, "imaging": 0, "lab-test": 0}
        language_counts = {}
        total_text_length = 0
        chunk_count = 0
        
        next_offset = None
        import re
        
        # Scan ALL points to get accurate stats and book list
        while True:
            points, next_offset = client.scroll(
                collection_name=Config.COLLECTION_NAME,
                limit=1000, 
                offset=next_offset,
                with_payload=["book_name", "author", "publish_year", "keywords", "language", "text", "pdf_id"],
                with_vectors=False
            )
            
            for point in points:
                payload = point.payload or {}
                raw_book_name = payload.get("book_name")
                if not raw_book_name: continue
                
                # Normalize book name to group split parts together
                # Removes suffixes like (1-342), (343-600), (1)
                book_name = re.sub(r'\(\d+(-\d+)?\)$', '', raw_book_name).strip()
                
                chunk_count += 1
                
                # Stats: Keywords
                keywords = payload.get("keywords", [])
                for kw in keywords:
                    kw_lower = kw.lower().strip()
                    if kw_lower in keyword_counts:
                        keyword_counts[kw_lower] += 1
                
                # Stats: Language
                lang = payload.get("language", "unknown")
                if lang:
                    lang_lower = lang.lower().strip()
                    language_counts[lang_lower] = language_counts.get(lang_lower, 0) + 1
                
                # Stats: Length
                text_len = len(payload.get("text", ""))
                total_text_length += text_len
                
                # Book Aggregation
                if book_name not in books_map:
                    raw_year = str(payload.get("publish_year", "Unknown"))
                    books_map[book_name] = {
                        "id": book_name, # Use normalized name as ID for grouping
                        "pdf_id": payload.get("pdf_id", "unknown"),
                        "title": book_name,
                        "author": payload.get("author", "Unknown"),
                        "year": raw_year,
                        "keywords": keywords[:4],
                        "stats": {
                            "qdrantPoints": 0, 
                            "avgChunkLength": 1000 # Placeholder
                        }
                    }
                
                books_map[book_name]["stats"]["qdrantPoints"] += 1

            if next_offset is None:
                break
        
        books = list(books_map.values())
        
        # Calculate global average chunk length
        avg_chunk_length = int(total_text_length / chunk_count) if chunk_count > 0 else 0
        
        # Update books stats with averages if needed, or keeping it simple
        # Estimate total collection size
        total_points_count = chunk_count
        estimated_total_bytes = total_points_count * (6144 + avg_chunk_length)
            
        return {
            "books": books,
            "stats": {
                "keyword_distribution": keyword_counts,
                "language_distribution": language_counts,
                "avg_chunk_length": avg_chunk_length,
                "total_size_bytes": estimated_total_bytes
            }
        }
        
    except Exception as e:
        print(f"[ERROR] Fetching library: {e}")
        return {"books": [], "stats": {"keyword_distribution": {}, "language_distribution": {}, "avg_chunk_length": 0}}

@app.delete("/library/{pdf_id}")
def delete_book(pdf_id: str):
    """Delete a book from the index using its pdf_id."""
    try:
        client = QdrantClient(url=Config.QDRANT_URL, port=443, api_key=Config.QDRANT_API_KEY)
        
        if not client.collection_exists(Config.COLLECTION_NAME):
            raise HTTPException(status_code=404, detail="Collection not found")

        # Delete points with matching pdf_id
        client.delete(
            collection_name=Config.COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[models.FieldCondition(key="pdf_id", match=models.MatchValue(value=pdf_id))])
            )
        )
        return {"message": f"Book with pdf_id '{pdf_id}' deleted successfully"}
        
    except Exception as e:
        print(f"[ERROR] Deleting book {pdf_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/{filename}")
def delete_raw_file(filename: str):
    """Delete a raw file from the database/raw directory."""
    try:
        # Basic sanitization to prevent directory traversal
        if ".." in filename or "/" in filename or "\\" in filename:
             raise HTTPException(status_code=400, detail="Invalid filename")
             
        file_path = Config.RAW_DIR / filename
        if file_path.exists():
            os.remove(file_path)
            print(f"[INFO] Deleted raw file: {file_path}")
            return {"message": f"File '{filename}' deleted"}
        else:
            raise HTTPException(status_code=404, detail="File not found")
            
    except Exception as e:
        print(f"[ERROR] Deleting raw file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vectors")
def get_vectors(limit: int = 200):
    """Fetch vectors with metadata for UMAP visualization."""
    try:
        client = QdrantClient(url=Config.QDRANT_URL, port=443, api_key=Config.QDRANT_API_KEY)
        
        if not client.collection_exists(Config.COLLECTION_NAME):
            return {"vectors": [], "points": []}
        
        # Scroll through points WITH vectors
        result, _ = client.scroll(
            collection_name=Config.COLLECTION_NAME,
            limit=limit,
            with_vectors=["dense"],
            with_payload=["book_name", "keywords"]
        )
        
        vectors = []
        points = []
        
        for point in result:
            if point.vector and "dense" in point.vector:
                vectors.append(point.vector["dense"])
                points.append({
                    "book": point.payload.get("book_name", "Unknown") if point.payload else "Unknown",
                    "keywords": point.payload.get("keywords", []) if point.payload else []
                })
        
        return {"vectors": vectors, "points": points}
        
    except Exception as e:
        print(f"[ERROR] Fetching vectors: {e}")
        return {"vectors": [], "points": [], "error": str(e)}

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

@app.websocket("/ws/pipeline")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)

# --- WebSocket Log Integration ---

running_loop = None


# Global variable to store the last checked display name for cleaner logging
last_checked_display_name = None

def parse_and_broadcast_log(message: str):
    """Parse log message and broadcast to UI."""
    # Replace temp filename with display name if available
    if last_checked_display_name and "gdown_temp_" in message:
        # Simple string replacement for better UI experience
        import re
        message = re.sub(r'gdown_temp_[a-zA-Z0-9_\-]+\.pdf', last_checked_display_name, message)
    
    # Default values
    msg_payload = {"message": message}
    
    # Try to parse Phase/Status
    # Format: PHASE: {phase_name} | STATUS: {status} | {details}
    if message.startswith("PHASE:"):
        ensure_parts = message.split("|")
        if len(ensure_parts) >= 2:
            phase_part = ensure_parts[0].replace("PHASE:", "").strip()
            status_part = ensure_parts[1].replace("STATUS:", "").strip()
            details_part = ensure_parts[2] if len(ensure_parts) > 2 else ""
            
            # Use the full message as display message, or just details?
            # User wants [INFO], so maybe just pass the raw message as "message"
            # But the UI expects "message" for the log line.
            
            # Map Phase to Step
            step_map = {"Split": 1, "Split & Metadata": 1, "OCR": 2, "OCR & Parsing": 2, "Embedding": 3}
            # Handle compound phases or loose matches
            step = 1
            for key, val in step_map.items():
                if key in phase_part: 
                    step = val
                    break
            
            # Map Status
            status_lower = status_part.lower()
            ui_status = "processing"
            if "completed" in status_lower: ui_status = "completed"
            elif "error" in status_lower: ui_status = "error"
            
            msg_payload["step"] = step
            msg_payload["status"] = ui_status
    
    if running_loop and manager:
        asyncio.run_coroutine_threadsafe(manager.broadcast(msg_payload), running_loop)

from modules.utils.pipeline_logger import pipeline_logger

@app.on_event("startup")
async def startup_event():
    try:
        global running_loop
        running_loop = asyncio.get_running_loop()
        
        # Register callback
        pipeline_logger.register_callback(parse_and_broadcast_log)
    except Exception as e:
        print(f"[ERROR] Startup event failed: {e}")

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
    clean: bool = Form(True),
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
            
            # Get file stats
            file_stats = {"size": 0, "pages": 0}
            display_name = pdf_file.name
            
            global last_checked_display_name
            last_checked_display_name = display_name
            try:
                if pdf_file.exists():
                     file_stats["size"] = pdf_file.stat().st_size
                     # Try to get page count if it's a valid PDF
                     try:
                         from pypdf import PdfReader
                         reader = PdfReader(str(pdf_file))
                         file_stats["pages"] = len(reader.pages)
                         if reader.metadata and reader.metadata.title:
                             title = reader.metadata.title
                             if len(title) > 60: title = title[:57] + "..."
                             display_name = title
                             last_checked_display_name = display_name
                     except: pass
            except: pass

            results.append({
                "filename": pdf_file.name,
                "display_name": display_name,
                "exists_local": len(existing_split) > 0,
                "exists_qdrant": q_check.get("exists", False),
                "qdrant_count": q_check.get("count", 0),
                "exists": len(existing_split) > 0 or q_check.get("exists", False),
                "count": max(len(existing_split), q_check.get("count", 0)),
                "stats": file_stats
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
