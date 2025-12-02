import os
import logging
from datetime import datetime
from qdrant_client import QdrantClient, models

def setup_logger(log_dir: str):
    """Set up logger to write to a file in the specified directory."""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "indexing_status.log")
    
    logger = logging.getLogger("QdrantVerifier")
    logger.setLevel(logging.INFO)
    
    # Check if handler already exists to avoid duplicate logs
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

def verify_and_retry_indexing(
    qdrant_manager,
    json_files: list[str],
    log_dir: str = "logs"
) -> bool:
    """
    Verify if all chunks from the provided JSON files are indexed in Qdrant.
    If chunks are missing, attempt to retry indexing them.
    
    Args:
        qdrant_manager: Instance of QdrantManager.
        json_files: List of paths to chunk JSON files.
        log_dir: Directory to save the log file.
        
    Returns:
        True if all chunks are indexed (after retry), False otherwise.
    """
    import json
    from pathlib import Path
    
    logger = setup_logger(log_dir)
    print("\n[VERIFY] Starting verification...")
    
    all_expected_ids = set()
    id_to_chunk = {}
    id_to_meta = {}
    
    total_expected = 0
    
    # 1. Collect all expected IDs
    for json_file in json_files:
        path = Path(json_file)
        if not path.exists(): continue
        
        try:
            with open(path, 'r', encoding='utf-8') as f: chunks = json.load(f)
            
            # Load metadata for this file to generate correct IDs
            book_meta = qdrant_manager.load_metadata(path.stem.replace("_chunks", ""))
            
            # Resolve book name logic (must match process_batch)
            b_name = book_meta.get("book_name") or book_meta.get("BOOK_NAME") or book_meta.get("Title") or "Unknown"
            
            for chunk in chunks:
                text = chunk['content']
                if not text or not text.strip(): continue # Skip empty texts as they are skipped in indexing
                
                page_num = chunk['metadata'].get('page_number', chunk['metadata'].get('page', "Unknown"))
                
                # Generate ID
                point_id = qdrant_manager.generate_id(b_name, page_num, text)
                
                all_expected_ids.add(point_id)
                id_to_chunk[point_id] = chunk
                id_to_meta[point_id] = book_meta
                total_expected += 1
                
        except Exception as e:
            print(f"[ERROR] Failed to read {path.name}: {e}")

    if not all_expected_ids:
        print("[WARN] No expected chunks found to verify.")
        return True

    print(f"[VERIFY] Checking {len(all_expected_ids)} chunks in Qdrant...")
    
    # 2. Check existence in Qdrant
    # We use retrieve to check which IDs exist
    missing_ids = []
    batch_size = 1000
    all_ids_list = list(all_expected_ids)
    
    for i in range(0, len(all_ids_list), batch_size):
        batch_ids = all_ids_list[i : i + batch_size]
        try:
            points = qdrant_manager.qdrant_client.retrieve(
                collection_name=qdrant_manager.Config.COLLECTION_NAME,
                ids=batch_ids,
                with_payload=False,
                with_vectors=False
            )
            found_ids = {p.id for p in points}
            missing_ids.extend([pid for pid in batch_ids if pid not in found_ids])
        except Exception as e:
            print(f"[ERROR] Failed to retrieve batch {i}: {e}")
            # Assume all missing in this batch if retrieval fails? 
            # Or maybe just continue? Let's assume missing to trigger retry.
            missing_ids.extend(batch_ids)

    # 3. Handle Missing
    if not missing_ids:
        msg = f"All {total_expected} chunks verified successfully."
        logger.info(msg)
        print(f"[SUCCESS] {msg}")
        return True
    
    print(f"[WARN] Found {len(missing_ids)} missing chunks. Retrying...")
    logger.warning(f"Missing {len(missing_ids)} chunks. Retrying...")
    
    # 4. Retry Logic
    # Group missing chunks by book/metadata to reuse process_batch logic effectively?
    # Actually process_batch takes a list of chunks and one book_meta.
    # But here chunks might come from different books if we process multiple files.
    # So we should group by book_meta (or just process one by one/batch by book).
    
    # Simple approach: Group by original file (we can't easily track back to file, but we have id_to_meta)
    # But process_batch expects a list of dicts.
    
    # Let's group by book_name to be safe, as process_batch uses one book_meta
    from collections import defaultdict
    retry_batches = defaultdict(list)
    
    for pid in missing_ids:
        chunk = id_to_chunk[pid]
        meta = id_to_meta[pid]
        # Use book name as key to group
        b_name = meta.get("book_name") or meta.get("BOOK_NAME") or meta.get("Title") or "Unknown"
        retry_batches[b_name].append((chunk, meta))
        
    retry_success = 0
    retry_failed = 0
    
    for b_name, items in retry_batches.items():
        # Unpack
        chunks = [item[0] for item in items]
        # Use metadata from first item (should be same for same book)
        book_meta = items[0][1]
        
        print(f"[RETRY] Retrying {len(chunks)} chunks for book '{b_name}'...")
        
        # Process in batches
        for i in range(0, len(chunks), qdrant_manager.Config.GEMINI_BATCH_SIZE):
            batch = chunks[i : i + qdrant_manager.Config.GEMINI_BATCH_SIZE]
            count = qdrant_manager.process_batch(batch, book_meta, f"retry_{i}")
            if count > 0:
                retry_success += count
            else:
                retry_failed += len(batch)

    # 5. Final Check
    print(f"[INFO] Retry finished. Success: {retry_success}, Failed: {retry_failed}")
    
    if retry_failed > 0:
        msg = f"Verification finished with {retry_failed} chunks still missing after retry. Success: {retry_success}."
        logger.error(msg)
        print(f"[ERROR] {msg}")
        return False
    else:
        msg = f"All missing chunks successfully re-indexed. Total Verified: {total_expected}."
        logger.info(msg)
        print(f"[SUCCESS] {msg}")
        return True
