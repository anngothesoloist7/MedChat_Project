import os
import shutil
import json
import re
from pathlib import Path
from typing import List, Tuple
from pypdf import PdfReader, PdfWriter
from mistralai import Mistral, DocumentURLChunk
from modules.utils.pipeline_logger import pipeline_logger
from modules.config import Config

try:
    import pypdfium2 as pdfium
    HAS_PDFIUM = True
except ImportError:
    HAS_PDFIUM = False

class PDFProcessor:
    def __init__(self):
        self.target_size = Config.TARGET_CHUNK_SIZE
        self.max_pages = Config.MAX_PAGES

    def get_pdf_info(self, path: Path) -> Tuple[int, int]:
        return len(PdfReader(str(path)).pages), path.stat().st_size

    def calculate_ranges(self, total_pages: int, total_size: int) -> List[Tuple[int, int]]:
        if total_size <= self.target_size and total_pages <= self.max_pages:
            return [(1, total_pages)]
        
        avg_size = total_size / total_pages if total_pages > 0 else 0
        pages_per_chunk = int(self.target_size / avg_size) if avg_size > 0 else self.max_pages
        pages_per_chunk = max(1, min(pages_per_chunk, self.max_pages))
        
        return [(i, min(i + pages_per_chunk - 1, total_pages)) 
                for i in range(1, total_pages + 1, pages_per_chunk)]

    def split_pdf(self, input_path: Path, output_dir: Path) -> List[Path]:
        total_pages, size = self.get_pdf_info(input_path)
        ranges = self.calculate_ranges(total_pages, size)
        
        if len(ranges) == 1 and ranges[0] == (1, total_pages):
            print(f"[INFO] No split needed for {input_path.name}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        reader = PdfReader(str(input_path))
        base_name = input_path.stem.replace("Bản sao của ", "").strip()
        output_files, failed = [], []

        for start, end in ranges:
            fname = f"{base_name}({start}-{end}).pdf" if start != end else f"{base_name}({start}).pdf"
            if start == 1 and end == total_pages: fname = f"{base_name}.pdf"
            out_path = output_dir / fname
            
            try:
                writer = PdfWriter()
                for p in range(start - 1, end):
                    try: writer.add_page(reader.pages[p])
                    except Exception: continue
                
                with open(out_path, 'wb') as f: writer.write(f)
                output_files.append(out_path)
                print(f"[SUCCESS] Created: {fname}")
                pipeline_logger.log_info(f"Created: {fname}")
            except Exception as e:
                print(f"[ERROR] pypdf failed for {fname}: {e}")
                if HAS_PDFIUM and self._fallback_pdfium(input_path, out_path, start, end):
                    output_files.append(out_path)
                    print(f"[SUCCESS] pypdfium2 fallback: {fname}")
                else:
                    failed.append((start, end))

        if failed: print(f"[WARN] {len(failed)} chunks failed.")
        return output_files

    def _fallback_pdfium(self, input_path: Path, output_path: Path, start: int, end: int) -> bool:
        try:
            pdf = pdfium.PdfDocument(str(input_path))
            new_pdf = pdfium.PdfDocument.new()
            new_pdf.import_pages(pdf, list(range(start - 1, end)))
            new_pdf.save(str(output_path))
            return True
        except Exception: return False

    def get_info(self, path: Path) -> dict:
        pages, size = self.get_pdf_info(path)
        return {'name': path.name, 'pages': pages, 'size_mb': size / 1048576, 'chunks': len(self.calculate_ranges(pages, size))}

def extract_metadata(file_path: Path, pdf_id: str = None):
    print(f"\n[INFO] Extracting metadata: {file_path.name}")
    pipeline_logger.log_info(f"Extracting metadata: {file_path.name}")
    if not Config.MISTRAL_API_KEY or not Config.GOOGLE_CHAT_API_KEY:
        return print("[ERROR] Missing API keys.")

    temp_pdf = Config.RAW_DIR / f"temp_meta_{file_path.name}"
    try:
        reader = PdfReader(str(file_path))
        writer = PdfWriter()
        for i in range(min(15, len(reader.pages))): writer.add_page(reader.pages[i])
        with open(temp_pdf, "wb") as f: writer.write(f)
            
        client = Mistral(api_key=Config.MISTRAL_API_KEY)
        print("[INFO] Uploading to Mistral...")
        with open(temp_pdf, "rb") as f:
            upload = client.files.upload(file={"file_name": temp_pdf.name, "content": f}, purpose="ocr")
        
        print("[INFO] OCR Processing...")
        ocr = client.ocr.process(
            document=DocumentURLChunk(document_url=client.files.get_signed_url(file_id=upload.id).url),
            model=Config.MISTRAL_MODEL, include_image_base64=False
        )
        client.files.delete(file_id=upload.id)
        
        full_text = "\n\n".join([p.markdown for p in ocr.pages])
        print("[INFO] Gemini Analysis with Google Search...")
        
        prompt_path = Config.BASE_DIR / "prompts" / "metadata_extract_prompt.md"
        if not prompt_path.exists(): return print(f"[ERROR] Prompt missing: {prompt_path}")
        
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=Config.GOOGLE_CHAT_API_KEY)
        prompt_content = prompt_path.read_text(encoding="utf-8")
        full_prompt = f"{prompt_content}\n\nTEXT CONTENT:\n{full_text[:50000]}"
        
        response = client.models.generate_content(
            model=Config.GEMINI_METADATA_MODEL,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=full_prompt)])],
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        )
        
        meta_json_str = response.text.strip()
        if "```" in meta_json_str: meta_json_str = meta_json_str.split("```json")[-1].split("```")[0].strip()
        
        try:
            meta_data = json.loads(meta_json_str)
            if pdf_id: meta_data["pdf_id"] = pdf_id
            meta_json = json.dumps(meta_data, indent=2, ensure_ascii=False)
        except Exception:
            print("[WARN] Failed to parse metadata JSON, saving raw string.")
            # Try to inject pdf_id into raw string if it looks like a JSON object
            if pdf_id and meta_json_str.strip().endswith("}"):
                 meta_json = meta_json_str.strip()[:-1] + f', "pdf_id": "{pdf_id}"}}'
            else:
                 meta_json = meta_json_str
            
        # Use same normalization as split_pdf to ensure consistency
        base_name = file_path.stem.replace("Bản sao của ", "").strip()
        meta_path = Config.RAW_DIR / f"{base_name}_metadata.json"
        
        meta_path.write_text(meta_json, encoding="utf-8")
        print(f"[SUCCESS] Metadata saved: {meta_path.name}")
        
    except Exception as e: 
        print(f"[ERROR] Metadata failed: {e}")
        # If it is a quota error (429), we MUST stop the process and notify the user
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            raise Exception("Gemini API Quota Exceeded. Please update your API key or try again later.")
        
        # For other critical metadata failures, we might also want to stop if metadata is strictly required
        # For now, let's enforce metadata presence as per user request to "stop whole process"
        raise Exception(f"Metadata Extraction Failed: {e}")
            
    finally: 
        if temp_pdf.exists(): os.remove(temp_pdf)

def check_qdrant_existence(pdf_path: Path) -> dict:
    from modules.utils.hash_utils import get_file_id
    from modules.embedding_qdrant import QdrantManager
    from qdrant_client import models
    
    pdf_id = get_file_id(str(pdf_path))
    try:
        q_manager = QdrantManager()
        if not q_manager.check_connections(): return {"exists": False, "error": "Connection failed"}
        q_manager.init_collection()
        
        count_res = q_manager.qdrant_client.count(
            collection_name=q_manager.Config.COLLECTION_NAME,
            count_filter=models.Filter(must=[models.FieldCondition(key="pdf_id", match=models.MatchValue(value=pdf_id))])
        )
        return {"exists": count_res.count > 0, "count": count_res.count, "pdf_id": pdf_id, "collection_name": q_manager.Config.COLLECTION_NAME}
    except Exception as e: return {"exists": False, "error": str(e)}

def run_splitter(input_path_str: str, overwrite: bool = False) -> List[str]:
    Config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    Config.SPLITTED_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(input_path_str)
    
    if not path.exists() or path.suffix.lower() != '.pdf':
        print(f"[ERROR] Invalid PDF: {input_path_str}")
        return []

    print(f"[INFO] Processing: {path.name}")
    
    def sanitize_filename(name: str, max_length: int = 100) -> str:
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        if len(name) > max_length:
            stem = Path(name).stem
            suffix = Path(name).suffix
            name = stem[:max_length-len(suffix)] + suffix
        return name

    safe_name = sanitize_filename(path.name)
    raw_path = Config.RAW_DIR / safe_name
    if path.resolve() != raw_path.resolve():
        shutil.copy2(path, raw_path)
        print(f"[INFO] Saved to raw: {raw_path}")

    q_check = check_qdrant_existence(raw_path)
    pdf_id = q_check.get("pdf_id", "unknown")
    points_deleted = False
    collection_status = "Unknown"
    
    if q_check.get("error"):
        print(f"[WARN] Qdrant check failed: {q_check['error']}")
        collection_status = f"Error: {q_check['error'][:50]}"
    elif q_check["exists"]:
        print(f"[WARN] Found {q_check['count']} existing points.")
        collection_status = "Exists"
        if not overwrite:
            print(f"[WARN] PDF '{path.name}' already exists in DB. Skipping (overwrite=False).")
            raise FileExistsError(f"PDF '{path.name}' already exists in Qdrant.")
            
        print(f"[INFO] Overwriting... Deleting existing points...")
        try:
            from modules.embedding_qdrant import QdrantManager
            from qdrant_client import models
            q_manager = QdrantManager()
            q_manager.qdrant_client.delete(
                collection_name=q_manager.Config.COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=[models.FieldCondition(key="pdf_id", match=models.MatchValue(value=pdf_id))])
                )
            )
            print("[SUCCESS] Deleted existing points.")
            points_deleted = True
        except Exception as e: print(f"[ERROR] Failed to delete points: {e}")
    else:
        print("[INFO] No existing points found.")
        collection_status = "New"

    extract_metadata(raw_path, pdf_id)
    proc = PDFProcessor()
    info = proc.get_info(raw_path)
    print(f"\n[INFO] {info['name']} | {info['size_mb']:.2f}MB | {info['pages']} pages | {info['chunks']} chunks")
    
    print("[INFO] Splitting...")
    pipeline_logger.log_info("Splitting...")
    split_files = proc.split_pdf(raw_path, Config.SPLITTED_DIR)
    print(f"[INFO] Done! Saved in: {Config.SPLITTED_DIR}")
    
    pipeline_logger.log_phase_1(
        pdf_name=path.name, file_id=pdf_id, exists=(points_deleted or q_check["exists"]), 
        collection_status=collection_status, points_deleted=points_deleted
    )
    return [str(p) for p in split_files]
