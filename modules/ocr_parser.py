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

def save_parsed_content(filename: str, markdown: str, chunks: list, json_pages: list):
    base = os.path.splitext(filename)[0]
    with open(os.path.join(Config.PARSED_DIR, f"{base}.md"), "w", encoding="utf-8") as f:
        f.write(markdown)
    
    data = [{"content": c.page_content, "metadata": c.metadata} for c in chunks]
    with open(os.path.join(Config.PARSED_DIR, f"{base}_chunks.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    with open(os.path.join(Config.PARSED_DIR, f"{base}_pages.json"), "w", encoding="utf-8") as f:
        json.dump(json_pages, f, indent=2, ensure_ascii=False)
        
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
        
        import itertools
        max_retries = 3
        ocr_start_total = time.time()

        for attempt in range(max_retries):
            # Spinner setup
            stop_spinner = threading.Event()
            
            def spin():
                spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
                start_time = time.time()
                while not stop_spinner.is_set():
                    elapsed = time.time() - start_time
                    sys.stdout.write(f"\r[WAIT] OCR Processing... {next(spinner)} {elapsed:.1f}s")
                    sys.stdout.flush()
                    time.sleep(0.1)
                sys.stdout.write("\r" + " "*60 + "\r") # Clear line

            t = threading.Thread(target=spin)
            t.start()

            try:
                # Important: include_image_base64=True is needed to get image IDs and descriptions, 
                # even if we don't embed the base64 string in the final markdown.
                ocr = client.ocr.process(
                    document=DocumentURLChunk(document_url=signed_url),
                    model=Config.MISTRAL_MODEL, include_image_base64=False
                )
                stop_spinner.set()
                t.join()
                break # Success
            except Exception as e:
                stop_spinner.set()
                t.join()
                
                error_str = str(e)
                # Check for 500/502/503/504 errors or Cloudflare HTML responses
                if any(code in error_str for code in ["500", "502", "503", "504"]) or "Internal server error" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = 10 * (2 ** attempt) # 10s, 20s, 40s (increased wait for server errors)
                        print(f"\n[WARN] OCR Server Error (Attempt {attempt+1}/{max_retries}). Retrying in {wait_time}s...")
                        
                        # Dynamic countdown
                        for remaining in range(wait_time, 0, -1):
                            sys.stdout.write(f"\r[WAIT] Cooling down... {remaining}s ")
                            sys.stdout.flush()
                            time.sleep(1)
                        sys.stdout.write("\r" + " "*40 + "\r")
                        continue
                
                # For other errors or if retries exhausted
                if attempt < max_retries - 1:
                    wait_time = 5 * (2 ** attempt)
                    print(f"\n[WARN] OCR failed (Attempt {attempt+1}/{max_retries}): {e}")
                    print(f"[INFO] Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise e # Re-raise after last attempt
            
        print(f"[INFO] OCR Done in {time.time()-ocr_start_total:.1f}s")
        
        pages_data, md_parts, json_pages = [], [], []
        for i, page in enumerate(ocr.pages):
            md = page.markdown
            # NOT embed base64 images into the markdown.
            # Keep the markdown as is (with ![id](id) placeholders and descriptions).
            
            current_page_num = start_page + i
            pages_data.append({'content': md, 'page': current_page_num})
            md_parts.append(md)
            
            # JSON Output Structure
            json_pages.append({
                "page": current_page_num,
                "content": md,
                "images": [img.id for img in page.images]
            })
            
        # Check language and translate if needed
        # Fix: Remove extension first, then remove split suffix to match original metadata file
        base_name_no_ext = filename.replace(".pdf", "")
        base_name = re.sub(r'\(\d+(-\d+)?\)$', '', base_name_no_ext).strip()
        meta_path = os.path.join(Config.BASE_DIR, "database", "raw", f"{base_name}_metadata.json")
        
        full_markdown = "\n\n".join(md_parts)
        is_translated = False
        
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    # Check multiple fields for language
                    lang = str(meta.get("language") or meta.get("LANGUAGE") or "").lower()
                    
                    # Check for Vietnamese indicators
                    if any(v in lang for v in ["vietnamese", "vi", "tiếng việt"]):
                        print(f"[INFO] Detected Vietnamese content (Language: {lang}). Translating...")
                        from modules.utils.translator import translator
                        if translator:
                            # Check if translation already exists
                            trans_base = filename.replace('.pdf', '')
                            trans_md_path = os.path.join(Config.PARSED_DIR, f"{trans_base}_translated.md")
                            trans_json_path = os.path.join(Config.PARSED_DIR, f"{trans_base}_translated_pages.json")
                            
                            if os.path.exists(trans_md_path) and os.path.exists(trans_json_path):
                                print(f"[INFO] Found existing translation for {filename}. Skipping API call.")
                                with open(trans_md_path, 'r', encoding='utf-8') as f:
                                    full_markdown = f.read()
                                with open(trans_json_path, 'r', encoding='utf-8') as f:
                                    pages_data = json.load(f)
                                is_translated = True
                            else:
                                # Use batch translation
                                translated_pages, full_translated_md = translator.translate_pages(pages_data)
                                
                                if full_translated_md and full_translated_md != full_markdown:
                                    full_markdown = full_translated_md
                                    is_translated = True
                                    
                                    # Update pages_data to the new translated structure
                                    pages_data = translated_pages
                                    
                                    with open(trans_md_path, "w", encoding="utf-8") as f:
                                        f.write(full_markdown)
                                        
                                    with open(trans_json_path, "w", encoding="utf-8") as f:
                                        json.dump(translated_pages, f, indent=2, ensure_ascii=False)
                                        
                                    print(f"[SUCCESS] Translation saved to {trans_md_path}")
                                else:
                                    print("[WARN] Translation returned empty or identical text.")
                        else:
                            print("[WARN] Translator not initialized.")
                    else:
                        print(f"[INFO] Content language: {lang}. Skipping translation.")
            except Exception as e:
                print(f"[WARN] Failed to read metadata or translate: {e}")
        else:
            print(f"[WARN] Metadata not found at {meta_path}. Skipping translation check.")

        chunks = parse_markdown_for_rag(pages_data, filename)
        
        # If translated, we might want to indicate that in the filename or metadata
        save_parsed_content(filename, full_markdown, chunks, json_pages)
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
