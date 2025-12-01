import os
import shutil
import json
import time
from pathlib import Path
from typing import List, Tuple
from pypdf import PdfReader, PdfWriter
from dotenv import load_dotenv
from mistralai import Mistral, DocumentURLChunk
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()

try:
    import pypdfium2 as pdfium
    HAS_PDFIUM = True
except ImportError:
    HAS_PDFIUM = False

class Config:
    # Default to 50MB if not set
    TARGET_CHUNK_SIZE_MB = int(os.getenv('TARGET_CHUNK_SIZE_MB', 50))
    TARGET_CHUNK_SIZE = TARGET_CHUNK_SIZE_MB * 1024 * 1024
    # Default to 500 pages if not set
    MAX_PAGES = int(os.getenv('MAX_PAGES', 500))
    
    BASE_DIR = Path(os.getcwd()) # Use current working directory
    RAW_FOLDER = BASE_DIR / "database" / "raw"
    SPLITTED_FOLDER = BASE_DIR / "database" / "splitted"
    
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class PDFProcessor:
    def __init__(self, target_size: int = None, max_pages: int = None):
        self.target_size = target_size or Config.TARGET_CHUNK_SIZE
        self.max_pages = max_pages or Config.MAX_PAGES

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
            print(f"[INFO] File {input_path.name} fits constraints. No split needed.")
        
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
                    print(f"[SUCCESS] Created with pypdfium2: {fname}")
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
        except Exception as e:
            print(f"[ERROR] Fallback failed: {e}")
            return False

    def get_info(self, path: Path) -> dict:
        pages, size = self.get_pdf_info(path)
        ranges = self.calculate_ranges(pages, size)
        return {
            'name': path.name, 'pages': pages, 'size_mb': size / 1048576,
            'chunks': len(ranges), 'ranges': ranges
        }

def extract_metadata(file_path: Path):
    """
    Extracts metadata from the first 15 pages of the book using Mistral OCR and Gemini.
    """
    print(f"\n[INFO] Extracting metadata for: {file_path.name}")
    
    if not Config.MISTRAL_API_KEY or not Config.GOOGLE_API_KEY:
        print("[ERROR] API keys missing. Cannot extract metadata.")
        return

    # 1. Create a temporary PDF with first 15 pages
    temp_pdf_path = Config.RAW_FOLDER / f"temp_meta_{file_path.name}"
    try:
        reader = PdfReader(str(file_path))
        writer = PdfWriter()
        num_pages = min(15, len(reader.pages))
        for i in range(num_pages):
            writer.add_page(reader.pages[i])
        
        with open(temp_pdf_path, "wb") as f:
            writer.write(f)
            
        # 2. OCR with Mistral
        client = Mistral(api_key=Config.MISTRAL_API_KEY)
        print(f"[INFO] Uploading first {num_pages} pages to Mistral OCR...")
        
        with open(temp_pdf_path, "rb") as f:
            file_upload = client.files.upload(
                file={"file_name": temp_pdf_path.name, "content": f},
                purpose="ocr"
            )
        signed_url = client.files.get_signed_url(file_id=file_upload.id)
        
        print("[INFO] Processing OCR...")
        ocr_response = client.ocr.process(
            document=DocumentURLChunk(document_url=signed_url.url),
            model="mistral-ocr-latest",
            include_image_base64=False 
        )
        
        # Cleanup Mistral file
        client.files.delete(file_id=file_upload.id)
        
        # Combine text
        full_text = "\n\n".join([page.markdown for page in ocr_response.pages])
        
        # 3. Extract with Gemini
        print("[INFO] Analyzing text with Gemini Pro Latest...")
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro-latest", 
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0
        )
        
        # Load prompt from file
        prompt_path = Config.BASE_DIR / "prompts" / "metadata_extract_prompt.md"
        if not prompt_path.exists():
            print(f"[ERROR] Prompt file not found: {prompt_path}")
            return

        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()

        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"TEXT CONTENT:\n{full_text[:50000]}")
        ]
        
        response = llm.invoke(messages)
        metadata_json = response.content.strip()
        
        # Clean markdown code blocks if present
        if "```json" in metadata_json:
            metadata_json = metadata_json.split("```json")[1].split("```")[0].strip()
        elif "```" in metadata_json:
            metadata_json = metadata_json.split("```")[1].split("```")[0].strip()
            
        # 4. Save JSON
        metadata_path = Config.RAW_FOLDER / f"{file_path.stem}_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(metadata_json)
            
        print(f"[SUCCESS] Metadata saved to: {metadata_path}")
        
    except Exception as e:
        print(f"[ERROR] Metadata extraction failed: {e}")
    finally:
        if temp_pdf_path.exists():
            os.remove(temp_pdf_path)

def run_splitter(input_path_str: str) -> List[str]:
    """
    Main entry point for the splitter module.
    Args:
        input_path_str: Path to the PDF file.
    Returns:
        List of paths to the split PDF files.
    """
    Config.RAW_FOLDER.mkdir(parents=True, exist_ok=True)
    Config.SPLITTED_FOLDER.mkdir(parents=True, exist_ok=True)

    path = Path(input_path_str)
    
    if not path.exists() or path.suffix.lower() != '.pdf':
        print(f"[ERROR] Invalid PDF file: {input_path_str}")
        return []

    print(f"[INFO] Processing: {path.name}")
    raw_path = Config.RAW_FOLDER / path.name
    
    # Copy to raw folder if it's not already there
    if path.resolve() != raw_path.resolve():
        shutil.copy2(path, raw_path)
        print(f"[INFO] Saved to raw: {raw_path}")

    # --- Run Metadata Extraction ---
    extract_metadata(raw_path)
    # -------------------------------

    proc = PDFProcessor()
    info = proc.get_info(raw_path)
    print(f"\n[INFO] Info: {info['name']} | {info['size_mb']:.2f}MB | {info['pages']} pages | {info['chunks']} chunks")
    
    print("[INFO] Splitting...")
    split_files = proc.split_pdf(raw_path, Config.SPLITTED_FOLDER)
    print(f"[INFO] Done! Saved in: {Config.SPLITTED_FOLDER}")
    
    return [str(p) for p in split_files]
