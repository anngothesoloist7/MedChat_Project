import os
import shutil
import argparse
from pathlib import Path
from dotenv import load_dotenv
from modules.splitter_metadata import run_splitter
from modules.ocr_parser import run_ocr_parser
from modules.embedding_qdrant import run_embedding
from modules.utils.file_utils import resolve_pdf_path

load_dotenv()

class Config:
    BASE_DIR = Path(os.getcwd())
    SPLITTED_DIR = BASE_DIR / "database" / "splitted"
    RAW_DIR = BASE_DIR / "database" / "raw"
    MODULES_DIR = BASE_DIR / "modules"

def get_split_files(original_pdf: Path) -> list[str]:
    """Finds existing split files for a given PDF."""
    return [str(p) for p in Config.SPLITTED_DIR.glob(f"{original_pdf.stem}(*-*).pdf")]

def clear_pycache():
    """Cleans up __pycache__."""
    print("[INFO] Clearing __pycache__...")
    
    targets = [Config.MODULES_DIR, Config.MODULES_DIR / "utils"]
    
    for target in targets:
        if target.exists():
            for p in target.rglob("__pycache__"):
                try: shutil.rmtree(p)
                except Exception: pass

from modules.utils.pipeline_logger import pipeline_logger

def process_pdf(pdf_file: Path, phases: dict):
    print(f"\n{'='*40}\nProcessing: {pdf_file.name}\n{'='*40}")
    pipeline_logger.log_info(f"Processing PDF: {pdf_file.name}")
    
    split_files = []

    # Phase 1: Split
    if phases['p1']:
        print("\n[INFO] Phase 1: Splitting...")
        pipeline_logger.log_phase("Split", "STARTED", f"File: {pdf_file.name}")
        try:
            split_files = run_splitter(str(pdf_file))
            if not split_files: 
                print("[ERROR] Splitting failed.")
                pipeline_logger.log_phase("Split", "FAILED", "No files generated")
                return
            print(f"[INFO] Generated {len(split_files)} files.")
            pipeline_logger.log_phase("Split", "COMPLETED", f"Generated {len(split_files)} files")
        except Exception as e:
            pipeline_logger.log_phase("Split", "ERROR", str(e))
            print(f"[ERROR] Split phase failed: {e}")
            return
    else:
        print("\n[INFO] Phase 1: Skipped (Checking existing...)")
        split_files = get_split_files(pdf_file)
        if not split_files: 
            print(f"[WARN] No split files found for {pdf_file.name}")
            pipeline_logger.log_phase("Split", "SKIPPED", "No existing split files found")
            return
        print(f"[INFO] Found {len(split_files)} existing files.")
        pipeline_logger.log_phase("Split", "SKIPPED", f"Found {len(split_files)} existing files")

    # Phase 2: OCR
    if phases['p2']:
        print("\n[INFO] Phase 2: OCR & Parsing...")
        pipeline_logger.log_phase("OCR", "STARTED", f"Files: {len(split_files)}")
        try:
            run_ocr_parser(split_files)
            pipeline_logger.log_phase("OCR", "COMPLETED")
        except Exception as e:
            pipeline_logger.log_phase("OCR", "ERROR", str(e))
            print(f"[ERROR] OCR phase failed: {e}")
    else: 
        print("\n[INFO] Phase 2: Skipped")
        pipeline_logger.log_phase("OCR", "SKIPPED")

    # Phase 3: Embedding
    if phases['p3']:
        print("\n[INFO] Phase 3: Embedding...")
        
        # Validate that all chunks exist before proceeding
        missing_chunks = []
        for sf in split_files:
            sf_path = Path(sf)
            # Check for standard chunks or translated chunks
            # Logic: If translated exists, we use that. Else standard.
            # But here we just need to ensure *something* exists for every file.
            # Actually, run_embedding handles the logic of picking the right file.
            # We just need to check if run_ocr_parser succeeded for all.
            
            # Simple check: look for {stem}_chunks.json or {stem}_translated_pages.json
            # Note: ocr_parser saves to {stem}_chunks.json ALWAYS (even if translated, it saves chunks there too? 
            # No, ocr_parser saves to {stem}_chunks.json at the end of process_file regardless of translation).
            # Wait, let's check ocr_parser.py...
            # Yes, save_parsed_content is called at the end. So {stem}_chunks.json should exist.
            
            chunk_path = Config.BASE_DIR / "database" / "parsed" / f"{sf_path.stem}_chunks.json"
            if not chunk_path.exists():
                missing_chunks.append(sf_path.name)
        
        if missing_chunks:
            msg = f"Missing chunks for {len(missing_chunks)} files: {missing_chunks}. Cannot proceed to Embedding."
            print(f"[ERROR] {msg}")
            pipeline_logger.log_phase("Embedding", "SKIPPED", msg)
        else:
            pipeline_logger.log_phase("Embedding", "STARTED")
            try:
                run_embedding(split_files)
                pipeline_logger.log_phase("Embedding", "COMPLETED")
            except Exception as e:
                pipeline_logger.log_phase("Embedding", "ERROR", str(e))
                print(f"[ERROR] Embedding phase failed: {e}")
    else: 
        print("\n[INFO] Phase 3: Skipped")
        pipeline_logger.log_phase("Embedding", "SKIPPED")

    # Cleanup if requested
    if phases['clean']:
        cleanup_temp_files(pdf_file)
        pipeline_logger.log_info(f"Cleanup completed for {pdf_file.name}")

def cleanup_temp_files(original_pdf: Path):
    """Removes temporary files from database folders."""
    print(f"\n[INFO] Cleaning up temporary files for {original_pdf.name}...")
    stem = original_pdf.stem
    
    # Define patterns to remove
    patterns = [
        Config.BASE_DIR / "database" / "raw" / f"{stem}*",
        Config.SPLITTED_DIR / f"{stem}*",
        Config.BASE_DIR / "database" / "parsed" / f"{stem}*"
    ]
    
    import glob
    count = 0
    for pattern in patterns:
        for f in glob.glob(str(pattern)):
            try:
                Path(f).unlink()
                count += 1
            except Exception as e:
                print(f"[WARN] Failed to delete {f}: {e}")
    print(f"[INFO] Removed {count} temporary files.")

def main():
    clear_pycache()
    parser = argparse.ArgumentParser(description="Medical RAG Pipeline")
    parser.add_argument("input_path", nargs="?", help="Input PDF path, directory, or URL")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3], help="Run specific phase")
    parser.add_argument("--clean", type=int, choices=[0, 1], default=0, help="Cleanup temp files (1: Yes, 0: No)")
    args = parser.parse_args()

    raw_input = args.input_path or input("Enter path or URL: ").strip('"')
    
    files = []
    
    # Check if input is a directory
    if os.path.isdir(raw_input):
        input_path = Path(raw_input)
        files = list(input_path.glob("*.pdf"))
    else:
        # Try to resolve as a single file or URL
        try:
            # Resolve/Download the file
            resolved_path = resolve_pdf_path(raw_input, download_dir=str(Config.RAW_DIR))
            files = [Path(resolved_path)]
        except Exception as e:
            print(f"[ERROR] {e}")
            return

    if not files: return print("[WARN] No PDF files found.")

    print(f"[INFO] Found {len(files)} files.")
    phases = {
        'p1': args.phase is None or args.phase == 1,
        'p2': args.phase is None or args.phase == 2,
        'p3': args.phase is None or args.phase == 3,
        'clean': args.clean == 1
    }

    for f in files: process_pdf(f, phases)
    print("\n[INFO] Pipeline Completed")

if __name__ == "__main__":
    main()
