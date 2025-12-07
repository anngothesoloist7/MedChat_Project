import os
from pathlib import Path
import time
import json
import threading
import re
import sys
from mistralai import Mistral, DocumentURLChunk
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from modules.utils.pipeline_logger import pipeline_logger
from modules.config import Config

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
        msg = "MISTRAL_API_KEY missing in .env"
        print(f"[ERROR] {msg}")
        pipeline_logger.log_phase("OCR", "ERROR", msg)
        return None
    return Mistral(api_key=Config.MISTRAL_API_KEY)

def upload_pdf(client: Mistral, file_path: str) -> tuple[str, str]:
    filename = os.path.basename(file_path)
    rate_tracker.wait_if_needed()
    print(f"[INFO] Uploading {filename}...")
    pipeline_logger.log_info(f"Uploading {filename}...")
    with open(file_path, "rb") as f:
        upload = client.files.upload(file={"file_name": filename, "content": f}, purpose="ocr")
    return upload.id, client.files.get_signed_url(file_id=upload.id).url

def save_parsed_content(filename: str, markdown: str, chunks: list, json_pages: list):
    base = os.path.splitext(filename)[0]
    with open(Config.PARSED_DIR / f"{base}.md", "w", encoding="utf-8") as f: f.write(markdown)
    
    data = [{"content": c.page_content, "metadata": c.metadata} for c in chunks]
    with open(Config.PARSED_DIR / f"{base}_chunks.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    with open(Config.PARSED_DIR / f"{base}_pages.json", "w", encoding="utf-8") as f:
        json.dump(json_pages, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Saved parsed content for {filename}")

def parse_markdown_for_rag(pages_data: list[dict], source_file: str):
    print("[INFO] Parsing markdown...")
    pipeline_logger.log_info("Parsing markdown...")
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
        pipeline_logger.log_info("Requesting OCR...")
        
        max_retries = 10
        ocr_start_total = time.time()

        for attempt in range(max_retries):
            try:
                ocr = client.ocr.process(
                    document=DocumentURLChunk(document_url=signed_url),
                    model=Config.MISTRAL_MODEL, include_image_base64=False
                )
                break 
            except Exception as e:
                error_str = str(e)
                if attempt < max_retries - 1:
                    wait_time = min(600, 30 * (2 ** attempt)) if any(c in error_str for c in ["500", "502", "503", "504", "Bad gateway"]) else 10 * (2 ** attempt)
                    print(f"\n[WARN] OCR Error (Attempt {attempt+1}/{max_retries}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else: raise e
            
        print(f"[INFO] OCR Done in {time.time()-ocr_start_total:.1f}s")
        pipeline_logger.log_info(f"OCR Done in {time.time()-ocr_start_total:.1f}s")
        
        pages_data, md_parts, json_pages = [], [], []
        for i, page in enumerate(ocr.pages):
            md = page.markdown
            current_page_num = start_page + i
            pages_data.append({'content': md, 'page': current_page_num})
            md_parts.append(md)
            json_pages.append({"page": current_page_num, "content": md, "images": [img.id for img in page.images]})
            
        base_name = re.sub(r'\(\d+(-\d+)?\)$', '', filename.replace(".pdf", "")).strip()
        meta_path = Config.RAW_DIR / f"{base_name}_metadata.json"
        full_markdown = "\n\n".join(md_parts)
        is_translated = False
        
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    lang = str(meta.get("language") or meta.get("LANGUAGE") or "").lower()
                    if any(v in lang for v in ["vietnamese", "vi", "tiếng việt"]):
                        print(f"[INFO] Translating Vietnamese content...")
                        from modules.utils.translator import translator
                        if translator:
                            trans_base = filename.replace('.pdf', '')
                            trans_md_path = Config.PARSED_DIR / f"{trans_base}_translated.md"
                            trans_json_path = Config.PARSED_DIR / f"{trans_base}_translated_pages.json"
                            
                            if trans_md_path.exists() and trans_json_path.exists():
                                print(f"[INFO] Found existing translation.")
                                full_markdown = trans_md_path.read_text(encoding='utf-8')
                                with open(trans_json_path, 'r', encoding='utf-8') as f: pages_data = json.load(f)
                                is_translated = True
                            else:
                                translated_pages, full_translated_md = translator.translate_pages(pages_data)
                                if full_translated_md and full_translated_md != full_markdown:
                                    full_markdown = full_translated_md
                                    is_translated = True
                                    pages_data = translated_pages
                                    trans_md_path.write_text(full_markdown, encoding="utf-8")
                                    with open(trans_json_path, "w", encoding="utf-8") as f:
                                        json.dump(translated_pages, f, indent=2, ensure_ascii=False)
                                    print(f"[SUCCESS] Translation saved.")
            except Exception as e: print(f"[WARN] Translation check failed: {e}")

        chunks = parse_markdown_for_rag(pages_data, filename)
        save_parsed_content(filename, full_markdown, chunks, json_pages)
        print(f"[SUCCESS] {filename}: {len(chunks)} chunks.")
        
        pipeline_logger.log_phase_2(
            split_file=filename, ocr_status="Success", translated=is_translated,
            chunks=len(chunks), time_taken=time.time() - ocr_start_total
        )
            
    except Exception as e:
        print(f"[ERROR] Failed {filename}: {e}")
        pipeline_logger.log_phase("OCR & Parsing", "ERROR", f"{filename} | {str(e)}")
    finally:
        if file_id:
            try: client.files.delete(file_id=file_id)
            except: pass

def run_ocr_parser(files: list[str]):
    if not files: return print("[WARN] No files for OCR.")
    print(f"[INFO] Starting OCR for {len(files)} files...")
    for f in files: process_file(f)
