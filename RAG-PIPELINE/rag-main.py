import argparse
import shutil
from pathlib import Path
from modules.config import Config
from modules.splitter_metadata import run_splitter
from modules.ocr_parser import run_ocr_parser
from modules.embedding_qdrant import run_embedding
from modules.utils.file_utils import resolve_pdf_path, list_google_drive_folder, download_google_drive_file, is_url
from modules.utils.pipeline_logger import pipeline_logger

def get_split_files(original_pdf: Path) -> list[str]:
    return [str(p) for p in Config.SPLITTED_DIR.glob(f"{original_pdf.stem}(*-*).pdf")]

def clear_pycache():
    print("[INFO] Clearing __pycache__...")
    modules_dir = Config.BASE_DIR / "modules"
    targets = [modules_dir, modules_dir / "utils"]
    for target in targets:
        if target.exists():
            for p in target.rglob("__pycache__"):
                try: shutil.rmtree(p)
                except Exception: pass

def process_pdf(pdf_file: Path, phases: dict):
    print(f"\n{'='*40}\nProcessing: {pdf_file.name}\n{'='*40}")
    pipeline_logger.log_info(f"Processing PDF: {pdf_file.name}")
    split_files = []

    # Phase 1: Split
    if phases['p1']:
        print("\n[INFO] Phase 1: Splitting...")
        pipeline_logger.log_phase("Split", "STARTED", f"File: {pdf_file.name}")
        try:
            split_files = run_splitter(str(pdf_file), overwrite=phases.get('overwrite', False))
            if not split_files: 
                print("[WARN] Splitting skipped or failed.")
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
        missing_chunks = []
        for sf in split_files:
            sf_path = Path(sf)
            chunk_path = Config.PARSED_DIR / f"{sf_path.stem}_chunks.json"
            if not chunk_path.exists():
                missing_chunks.append(sf_path.name)
        
        if missing_chunks:
            msg = f"Missing chunks for {len(missing_chunks)} files. Cannot proceed to Embedding."
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

    if phases['clean']:
        cleanup_temp_files(pdf_file)

def cleanup_temp_files(original_pdf: Path):
    print(f"\n[INFO] Cleaning up temporary files for {original_pdf.name}...")
    stem = original_pdf.stem
    patterns = [
        Config.RAW_DIR / f"{stem}*",
        Config.SPLITTED_DIR / f"{stem}*",
        Config.PARSED_DIR / f"{stem}*"
    ]
    import glob
    count = 0
    for pattern in patterns:
        for f in glob.glob(str(pattern)):
            try:
                Path(f).unlink()
                count += 1
            except Exception: pass
    print(f"[INFO] Removed {count} temporary files.")

def handle_input_source(input_path: str) -> list[dict]:
    path = Path(input_path)
    if path.is_dir():
        return [{'name': p.name, 'path': p, 'type': 'local'} for p in path.glob("*.pdf")]
    if is_url(input_path):
        if "drive.google.com" in input_path and "folders" in input_path:
             files = list_google_drive_folder(input_path)
             return [{'name': f['name'], 'url': f['url'], 'type': 'gdrive'} for f in files]
        return [{'name': 'Single URL File', 'url': input_path, 'type': 'url'}]
    if path.is_file() and path.suffix == ".pdf":
        return [{'name': path.name, 'path': path, 'type': 'local'}]
    return []

def main():
    clear_pycache()
    parser = argparse.ArgumentParser(description="Medical RAG Pipeline")
    parser.add_argument("input_path", nargs="?", help="Input PDF path, directory, or URL")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3], help="Run specific phase")
    parser.add_argument("--clean", type=int, choices=[0, 1], default=0, help="Cleanup temp files")
    args = parser.parse_args()

    raw_input = args.input_path or input("Enter path or URL: ").strip('"')
    candidates = handle_input_source(raw_input)
    
    if not candidates: return print("[WARN] No PDF files found.")

    print(f"\n[INFO] Found {len(candidates)} files:")
    for i, f in enumerate(candidates[:20]):
        print(f"{i+1}. {f['name']}")
    if len(candidates) > 20: print(f"... and {len(candidates)-20} more.")

    selected = candidates
    if len(candidates) > 1:
        choice = input(f"\nHow many files to process? (Enter number 1-{len(candidates)} or 'all'): ").strip().lower()
        if choice != 'all':
            try:
                limit = int(choice)
                if 1 <= limit <= len(candidates): selected = candidates[:limit]
            except ValueError: pass

    print(f"\n[INFO] Processing {len(selected)} files...")
    final_files = []
    for item in selected:
        try:
            if item['type'] == 'local':
                final_files.append(item['path'])
            elif item['type'] == 'gdrive':
                print(f"[INFO] Downloading {item['name']}...")
                final_files.append(Path(download_google_drive_file(item['url'], output_dir=str(Config.RAW_DIR))))
            elif item['type'] == 'url':
                final_files.append(Path(resolve_pdf_path(item['url'], download_dir=str(Config.RAW_DIR))))
        except Exception as e:
            print(f"[ERROR] Failed to prepare {item['name']}: {e}")

    phases = {
        'p1': args.phase is None or args.phase == 1,
        'p2': args.phase is None or args.phase == 2,
        'p3': args.phase is None or args.phase == 3,
        'clean': args.clean == 1
    }

    for f in final_files: process_pdf(f, phases)
    print("\n[INFO] Pipeline Completed")

if __name__ == "__main__":
    main()
