import os
import shutil
import argparse
from pathlib import Path
from dotenv import load_dotenv
from modules.splitter_metadata import run_splitter
from modules.ocr_parser import run_ocr_parser
from modules.embedding_qdrant import run_embedding

load_dotenv()

class Config:
    BASE_DIR = Path(os.getcwd())
    SPLITTED_DIR = BASE_DIR / "database" / "splitted"
    MODULES_DIR = BASE_DIR / "modules"

def get_split_files(original_pdf: Path) -> list[str]:
    """Finds existing split files for a given PDF."""
    return [str(p) for p in Config.SPLITTED_DIR.glob(f"{original_pdf.stem}(*-*).pdf")]

def clear_pycache():
    """Cleans up __pycache__."""
    print("[INFO] Clearing __pycache__...")
    if Config.MODULES_DIR.exists():
        for p in Config.MODULES_DIR.rglob("__pycache__"):
            try: shutil.rmtree(p)
            except Exception: pass

def process_pdf(pdf_file: Path, phases: dict):
    print(f"\n{'='*40}\nProcessing: {pdf_file.name}\n{'='*40}")
    split_files = []

    # Phase 1: Split
    if phases['p1']:
        print("\n[INFO] Phase 1: Splitting...")
        split_files = run_splitter(str(pdf_file))
        if not split_files: return print("[ERROR] Splitting failed.")
        print(f"[INFO] Generated {len(split_files)} files.")
    else:
        print("\n[INFO] Phase 1: Skipped (Checking existing...)")
        split_files = get_split_files(pdf_file)
        if not split_files: return print(f"[WARN] No split files found for {pdf_file.name}")
        print(f"[INFO] Found {len(split_files)} existing files.")

    # Phase 2: OCR
    if phases['p2']:
        print("\n[INFO] Phase 2: OCR & Parsing...")
        run_ocr_parser(split_files)
    else: print("\n[INFO] Phase 2: Skipped")

    # Phase 3: Embedding
    if phases['p3']:
        print("\n[INFO] Phase 3: Embedding...")
        run_embedding(split_files)
    else: print("\n[INFO] Phase 3: Skipped")

    # Cleanup if requested
    if phases['clean']:
        cleanup_temp_files(pdf_file)

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
    parser.add_argument("input_path", nargs="?", help="Input PDF or directory")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3], help="Run specific phase")
    parser.add_argument("--clean", type=int, choices=[0, 1], default=0, help="Cleanup temp files (1: Yes, 0: No)")
    args = parser.parse_args()

    input_path = Path(args.input_path or input("Enter path: ").strip('"'))
    if not input_path.exists(): return print(f"[ERROR] Invalid path: {input_path}")

    files = list(input_path.glob("*.pdf")) if input_path.is_dir() else [input_path] if input_path.suffix.lower() == '.pdf' else []
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
