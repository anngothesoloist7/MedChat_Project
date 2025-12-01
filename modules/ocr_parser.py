import os
import time
import json
import sys
import threading
import re
from dotenv import load_dotenv
from mistralai import Mistral, DocumentURLChunk
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Load environment variables
load_dotenv()

# --- Configuration ---
# We'll rely on the caller or default to current working directory structure
BASE_DIR = os.getcwd()
PARSED_DIR = os.path.join(BASE_DIR, "database", "parsed")
os.makedirs(PARSED_DIR, exist_ok=True)

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MAX_REQUESTS_PER_MINUTE = 20

# Chunking Config
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))

class RateLimitTracker:
    def __init__(self, limit: int = MAX_REQUESTS_PER_MINUTE):
        self.requests_made = 0
        self.last_reset = time.time()
        self.limit = limit
        
    def wait_if_needed(self):
        current_time = time.time()
        if current_time - self.last_reset >= 60:
            self.requests_made = 0
            self.last_reset = current_time
            
        if self.requests_made >= self.limit:
            wait_time = 60 - (current_time - self.last_reset) + 1
            print(f"[INFO] Rate limit hit. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            self.requests_made = 0
            self.last_reset = time.time()
            
        self.requests_made += 1

rate_tracker = RateLimitTracker()

def get_mistral_client():
    if not MISTRAL_API_KEY:
        print("[ERROR] MISTRAL_API_KEY not found in .env")
        return None
    return Mistral(api_key=MISTRAL_API_KEY)

def upload_pdf(client: Mistral, file_path: str) -> tuple[str, str]:
    filename = os.path.basename(file_path)
    rate_tracker.wait_if_needed()
    print(f"[INFO] Uploading {filename}...")
    with open(file_path, "rb") as f:
        file_upload = client.files.upload(
            file={"file_name": filename, "content": f},
            purpose="ocr"
        )
    signed_url = client.files.get_signed_url(file_id=file_upload.id)
    return file_upload.id, signed_url.url

def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    for img_name, base64_str in images_dict.items():
        replacement = f"![{img_name}]({img_name})"
        markdown_str = markdown_str.replace(f"![{img_name}]({img_name})", f"![{img_name}](data:image/jpeg;base64,{base64_str})")
    return markdown_str

def save_ocr_json(filename: str, ocr_response):
    """Saves the raw OCR response to a JSON file."""
    base_name = os.path.splitext(filename)[0]
    json_path = os.path.join(PARSED_DIR, f"{base_name}_ocr.json")
    
    try:
        if hasattr(ocr_response, "model_dump"):
            data = ocr_response.model_dump()
        elif hasattr(ocr_response, "dict"):
            data = ocr_response.dict()
        else:
            data = ocr_response.__dict__
            
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Saved raw OCR JSON: {json_path}")
    except Exception as e:
        print(f"[WARN] Failed to save OCR JSON: {e}")

def save_parsed_content(filename: str, markdown_content: str, chunks: list):
    base_name = os.path.splitext(filename)[0]
    
    md_path = os.path.join(PARSED_DIR, f"{base_name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"[INFO] Saved markdown: {md_path}")

    chunks_data = [{"content": c.page_content, "metadata": c.metadata} for c in chunks]
    json_path = os.path.join(PARSED_DIR, f"{base_name}_chunks.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Saved chunks: {json_path}")

def parse_markdown_for_rag(pages_data: list[dict], source_file: str):
    """
    Parses markdown pages for Hybrid RAG.
    """
    print("[INFO] Parsing markdown with structure and page tracking...")
    
    documents = []
    for page in pages_data:
        doc = Document(
            page_content=page['content'],
            metadata={
                "source": source_file,
                "page": page['page'],
                "parsing_method": "mistral_ocr_page_aware"
            }
        )
        documents.append(doc)

    separators = ["\n\n", "\n", "$$", " ", ""]
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=separators,
        keep_separator=True
    )
    
    final_chunks = text_splitter.split_documents(documents)
    
    for i, chunk in enumerate(final_chunks):
        chunk.metadata["chunk_index"] = i
        
    return final_chunks

def process_file(file_path: str):
    filename = os.path.basename(file_path)
    client = get_mistral_client()
    if not client: return

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"\n[INFO] Processing: {filename} ({file_size_mb:.2f} MB)")
    
    start_page = 1
    match = re.search(r"\((\d+)-(\d+)\)\.pdf$", filename)
    if match:
        start_page = int(match.group(1))
        print(f"[INFO] Detected start page from filename: {start_page}")
    
    (file_id, signed_url) = (None, None)
    try:
        file_id, signed_url = upload_pdf(client, file_path)
        
        rate_tracker.wait_if_needed()
        print(f"[INFO] Requesting OCR (This may take a while)...")
        
        start_time = time.time()
        stop_event = threading.Event()
        
        def show_progress():
            while not stop_event.is_set():
                elapsed = time.time() - start_time
                sys.stdout.write(f"\r[WAIT] OCR Processing... {elapsed:.1f}s elapsed")
                sys.stdout.flush()
                time.sleep(0.5)
        
        progress_thread = threading.Thread(target=show_progress)
        progress_thread.start()
        
        try:
            ocr_response = client.ocr.process(
                document=DocumentURLChunk(document_url=signed_url),
                model="mistral-ocr-latest",
                include_image_base64=True
            )
        finally:
            stop_event.set()
            progress_thread.join()
            sys.stdout.write("\n")
            
        print(f"[INFO] OCR Completed in {time.time() - start_time:.1f}s")
        
        save_ocr_json(filename, ocr_response)
        
        pages_data = []
        full_markdown_parts = []
        
        for i, page in enumerate(ocr_response.pages):
            image_data = {img.id: img.image_base64 for img in page.images}
            page_md = replace_images_in_markdown(page.markdown, image_data)
            
            current_page_num = start_page + i
            pages_data.append({
                'content': page_md,
                'page': current_page_num
            })
            full_markdown_parts.append(page_md)
            
        full_markdown = "\n\n".join(full_markdown_parts)
        chunks = parse_markdown_for_rag(pages_data, filename)
        save_parsed_content(filename, full_markdown, chunks)
        
        print(f"[SUCCESS] {filename}: {len(chunks)} chunks generated.")
            
    except Exception as e:
        print(f"[ERROR] Failed {filename}: {e}")
    finally:
        if file_id:
            try:
                client.files.delete(file_id=file_id)
                print(f"[INFO] Deleted temporary file from cloud: {file_id}")
            except Exception as cleanup_error:
                print(f"[WARN] Failed to delete file {file_id}: {cleanup_error}")

def run_ocr_parser(files: list[str]):
    """
    Main entry point for the OCR parser module.
    Args:
        files: List of PDF file paths to process.
    """
    if not files:
        print("[WARN] No files provided for OCR processing.")
        return

    print(f"[INFO] Starting OCR processing for {len(files)} files...")
    for pdf_file in files:
        process_file(pdf_file)
