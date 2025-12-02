import os
import shutil
import json
from pathlib import Path
from typing import List, Tuple
from pypdf import PdfReader, PdfWriter
from dotenv import load_dotenv
from mistralai import Mistral, DocumentURLChunk
from mistralai import Mistral, DocumentURLChunk

load_dotenv()

try:
    import pypdfium2 as pdfium
    HAS_PDFIUM = True
except ImportError:
    HAS_PDFIUM = False

class Config:
    TARGET_CHUNK_SIZE = int(os.getenv('TARGET_CHUNK_SIZE_MB', 50)) * 1024 * 1024
    MAX_PAGES = int(os.getenv('MAX_PAGES', 500))
    BASE_DIR = Path(os.getcwd())
    RAW_FOLDER = BASE_DIR / "database" / "raw"
    SPLITTED_FOLDER = BASE_DIR / "database" / "splitted"
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_CHAT_API_KEY")
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-ocr-latest")
    GEMINI_MODEL = os.getenv("GEMINI_METADATA_MODEL", "gemini-pro-latest")

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

def extract_metadata(file_path: Path):
    print(f"\n[INFO] Extracting metadata: {file_path.name}")
    if not Config.MISTRAL_API_KEY or not Config.GOOGLE_API_KEY:
        return print("[ERROR] Missing API keys.")

    temp_pdf = Config.RAW_FOLDER / f"temp_meta_{file_path.name}"
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
        full_text = "\n\n".join([p.markdown for p in ocr.pages])
        print("[INFO] Gemini Analysis with Google Search...")
        
        prompt_path = Config.BASE_DIR / "prompts" / "metadata_extract_prompt.md"
        if not prompt_path.exists(): return print(f"[ERROR] Prompt missing: {prompt_path}")
        
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=Config.GOOGLE_API_KEY)
        
        # Combine prompt and text
        prompt_content = prompt_path.read_text(encoding="utf-8")
        full_prompt = f"{prompt_content}\n\nTEXT CONTENT:\n{full_text[:50000]}"
        
        # Generate with Google Search Grounding
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=full_prompt)]
                )
            ],
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        meta_json = response.text.strip()
        if "```" in meta_json: meta_json = meta_json.split("```json")[-1].split("```")[0].strip()
            
        meta_path = Config.RAW_FOLDER / f"{file_path.stem}_metadata.json"
        meta_path.write_text(meta_json, encoding="utf-8")
        print(f"[SUCCESS] Metadata saved: {meta_path.name}")
        
    except Exception as e: print(f"[ERROR] Metadata failed: {e}")
    finally: 
        if temp_pdf.exists(): os.remove(temp_pdf)

def run_splitter(input_path_str: str) -> List[str]:
    Config.RAW_FOLDER.mkdir(parents=True, exist_ok=True)
    Config.SPLITTED_FOLDER.mkdir(parents=True, exist_ok=True)
    path = Path(input_path_str)
    
    if not path.exists() or path.suffix.lower() != '.pdf':
        print(f"[ERROR] Invalid PDF: {input_path_str}")
        return []

    print(f"[INFO] Processing: {path.name}")
    raw_path = Config.RAW_FOLDER / path.name
    if path.resolve() != raw_path.resolve():
        shutil.copy2(path, raw_path)
        print(f"[INFO] Saved to raw: {raw_path}")

    extract_metadata(raw_path)
    proc = PDFProcessor()
    info = proc.get_info(raw_path)
    print(f"\n[INFO] {info['name']} | {info['size_mb']:.2f}MB | {info['pages']} pages | {info['chunks']} chunks")
    
    print("[INFO] Splitting...")
    split_files = proc.split_pdf(raw_path, Config.SPLITTED_FOLDER)
    print(f"[INFO] Done! Saved in: {Config.SPLITTED_FOLDER}")
    return [str(p) for p in split_files]
