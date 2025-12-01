import os
import sys
import glob
from pathlib import Path
from modules.splitter_metadata import run_splitter
from modules.ocr_parser import run_ocr_parser
from modules.embedding_qdrant import run_embedding

def main():
    print("--- Medical RAG Pipeline ---")

    # 1. Get Input
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = input("Enter path to PDF file or directory: ").strip().strip('"')

    input_path = Path(input_path)
    pdf_files = []

    if input_path.is_dir():
        pdf_files = list(input_path.glob("*.pdf"))
    elif input_path.exists() and input_path.suffix.lower() == '.pdf':
        pdf_files = [input_path]
    else:
        print(f"[ERROR] Invalid input: {input_path}")
        return

    if not pdf_files:
        print("[WARN] No PDF files found.")
        return

    print(f"[INFO] Found {len(pdf_files)} files to process.")

    for pdf_file in pdf_files:
        print(f"\n{'='*40}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*40}")

        # 2. Run Splitter (Phase 1)
        print("\n[INFO] Phase 1: PDF Splitting and Metadata Extracting")
        split_files = run_splitter(str(pdf_file))
        
        if not split_files:
            print("[ERROR] Splitting failed. Skipping to next file.")
            continue

        print(f"[INFO] Generated {len(split_files)} split files.")

        # 3. Run OCR & Parsing (Phase 2)
        print("\n[INFO] Phase 2: OCR & Parsing with Chunking")
        run_ocr_parser(split_files)

        # 4. Run Embedding & Indexing (Phase 3)
        print("\n[INFO] Phase 3: Embedding & Indexing")
        run_embedding(split_files)

    print("\n[INFO] Pipeline Completed Successfully")

if __name__ == "__main__":
    main()
