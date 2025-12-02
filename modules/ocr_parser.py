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

load_dotenv()

class Config:
    BASE_DIR = os.getcwd()
    PARSED_DIR = os.path.join(BASE_DIR, "database", "parsed")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-ocr-latest")
    MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", 20))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))

os.makedirs(Config.PARSED_DIR, exist_ok=True)

class RateLimitTracker:
    def __init__(self):
        self.requests = 0
        self.last_reset = time.time()
        self.limit = Config.MAX_REQUESTS_PER_MINUTE
        
    def wait_if_needed(self):
        now = time.time()
        if now - self.last_reset >= 60:
            self.requests = 0
            self.last_reset = now
            
        if self.requests >= self.limit:
            wait = 60 - (now - self.last_reset) + 1
            print(f"[INFO] Rate limit hit. Waiting {wait:.1f}s...")
            time.sleep(wait)
            self.requests = 0
            self.last_reset = time.time()
        self.requests += 1

rate_tracker = RateLimitTracker()

def get_mistral_client():
    if not Config.MISTRAL_API_KEY:
        print("[ERROR] MISTRAL_API_KEY missing")
        return None
    return Mistral(api_key=Config.MISTRAL_API_KEY)

def upload_pdf(client: Mistral, file_path: str) -> tuple[str, str]:
    filename = os.path.basename(file_path)
    rate_tracker.wait_if_needed()
    print(f"[INFO] Uploading {filename}...")
    with open(file_path, "rb") as f:
        upload = client.files.upload(file={"file_name": filename, "content": f}, purpose="ocr")
    return upload.id, client.files.get_signed_url(file_id=upload.id).url

def save_parsed_content(filename: str, markdown: str, chunks: list):
    base = os.path.splitext(filename)[0]
    with open(os.path.join(Config.PARSED_DIR, f"{base}.md"), "w", encoding="utf-8") as f:
        f.write(markdown)
    
    data = [{"content": c.page_content, "metadata": c.metadata} for c in chunks]
    with open(os.path.join(Config.PARSED_DIR, f"{base}_chunks.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Saved parsed content for {filename}")

def parse_markdown_for_rag(pages_data: list[dict], source_file: str):
    print("[INFO] Parsing markdown...")
    docs = [Document(page_content=p['content'], metadata={"source": source_file, "page_number": p['page']}) for p in pages_data]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=Config.CHUNK_SIZE, chunk_overlap=Config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "$$", " ", ""], keep_separator=True
    )
    chunks = splitter.split_documents(docs)
    for i, c in enumerate(chunks): c.metadata["chunk_index"] = i
    return chunks

def process_file(file_path: str):
    filename = os.path.basename(file_path)
    client = get_mistral_client()
    if not client: return

    print(f"\n[INFO] Processing: {filename} ({os.path.getsize(file_path)/(1024*1024):.2f} MB)")
    start_page = 1
    match = re.search(r"\((\d+)-(\d+)\)\.pdf$", filename)
    if match: start_page = int(match.group(1))
    
    file_id = None
    try:
        file_id, signed_url = upload_pdf(client, file_path)
        rate_tracker.wait_if_needed()
        print(f"[INFO] Requesting OCR...")
        
        start = time.time()
        stop_event = threading.Event()
        t = threading.Thread(target=lambda: [time.sleep(0.5), sys.stdout.write(f"\r[WAIT] OCR... {time.time()-start:.1f}s")] and None if not stop_event.is_set() else None)
        t.start()
        
        try:
            ocr = client.ocr.process(
                document=DocumentURLChunk(document_url=signed_url),
                model=Config.MISTRAL_MODEL, include_image_base64=False
            )
        finally:
            stop_event.set()
            t.join()
            sys.stdout.write("\n")
            
        print(f"[INFO] OCR Done in {time.time()-start:.1f}s")
        
        pages_data, md_parts = [], []
        for i, page in enumerate(ocr.pages):
            md = page.markdown
            for img in page.images: md = md.replace(f"![{img.id}]({img.id})", f"![{img.id}](data:image/jpeg;base64,{img.image_base64})")
            pages_data.append({'content': md, 'page': start_page + i})
            md_parts.append(md)
            
        chunks = parse_markdown_for_rag(pages_data, filename)
        save_parsed_content(filename, "\n\n".join(md_parts), chunks)
        print(f"[SUCCESS] {filename}: {len(chunks)} chunks.")
            
    except Exception as e: print(f"[ERROR] Failed {filename}: {e}")
    finally:
        if file_id:
            try: client.files.delete(file_id=file_id)
            except: pass

def run_ocr_parser(files: list[str]):
    if not files: return print("[WARN] No files for OCR.")
    print(f"[INFO] Starting OCR for {len(files)} files...")
    for f in files: process_file(f)
