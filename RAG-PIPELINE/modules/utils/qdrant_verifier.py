import os
import json
import logging
from pathlib import Path
from collections import defaultdict
from modules.config import Config

def setup_logger(log_dir: str):
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger("QdrantVerifier")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(os.path.join(log_dir, "indexing_status.log"), encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)
    return logger

def verify_and_retry_indexing(qdrant_manager, json_files: list[str], log_dir: str = None) -> bool:
    log_dir = log_dir or str(Config.LOGS_DIR)
    logger = setup_logger(log_dir)
    print("\n[VERIFY] Starting verification...")
    
    all_expected_ids, id_to_chunk, id_to_meta = set(), {}, {}
    total_expected = 0
    
    for json_file in json_files:
        path = Path(json_file)
        if not path.exists(): continue
        try:
            with open(path, 'r', encoding='utf-8') as f: chunks = json.load(f)
            book_meta = qdrant_manager.load_metadata(path.stem.replace("_chunks", ""))
            b_name = book_meta.get("book_name") or book_meta.get("BOOK_NAME") or book_meta.get("Title") or "Unknown"
            
            for chunk in chunks:
                if not chunk['content'] or not chunk['content'].strip(): continue
                point_id = qdrant_manager.generate_id(b_name, chunk['metadata'].get('page_number', chunk['metadata'].get('page', "Unknown")), chunk['content'])
                all_expected_ids.add(point_id)
                id_to_chunk[point_id] = chunk
                id_to_meta[point_id] = book_meta
                total_expected += 1
        except Exception as e: print(f"[ERROR] Failed to read {path.name}: {e}")

    if not all_expected_ids: return True
    print(f"[VERIFY] Checking {len(all_expected_ids)} chunks in Qdrant...")
    
    missing_ids = []
    all_ids_list = list(all_expected_ids)
    for i in range(0, len(all_ids_list), 1000):
        batch_ids = all_ids_list[i : i + 1000]
        try:
            points = qdrant_manager.qdrant_client.retrieve(collection_name=qdrant_manager.Config.COLLECTION_NAME, ids=batch_ids, with_payload=False, with_vectors=False)
            found_ids = {p.id for p in points}
            missing_ids.extend([pid for pid in batch_ids if pid not in found_ids])
        except Exception as e:
            print(f"[ERROR] Batch retrieve failed: {e}")
            missing_ids.extend(batch_ids)

    if not missing_ids:
        logger.info(f"All {total_expected} chunks verified.")
        print(f"[SUCCESS] All {total_expected} chunks verified.")
        return True
    
    print(f"[WARN] Found {len(missing_ids)} missing chunks. Retrying...")
    logger.warning(f"Missing {len(missing_ids)} chunks. Retrying...")
    
    retry_batches = defaultdict(list)
    for pid in missing_ids:
        meta = id_to_meta[pid]
        b_name = meta.get("book_name") or meta.get("BOOK_NAME") or meta.get("Title") or "Unknown"
        retry_batches[b_name].append((id_to_chunk[pid], meta))
        
    retry_success, retry_failed = 0, 0
    for b_name, items in retry_batches.items():
        chunks = [item[0] for item in items]
        book_meta = items[0][1]
        print(f"[RETRY] Retrying {len(chunks)} chunks for '{b_name}'...")
        
        for i in range(0, len(chunks), qdrant_manager.Config.GEMINI_BATCH_SIZE):
            batch = chunks[i : i + qdrant_manager.Config.GEMINI_BATCH_SIZE]
            count = qdrant_manager.process_batch(batch, book_meta, f"retry_{i}")
            if count > 0: retry_success += count
            else: retry_failed += len(batch)

    print(f"[INFO] Retry finished. Success: {retry_success}, Failed: {retry_failed}")
    if retry_failed > 0:
        logger.error(f"Verification finished with {retry_failed} missing.")
        print(f"[ERROR] Verification finished with {retry_failed} missing.")
        return False
    else:
        logger.info(f"All missing chunks re-indexed. Total: {total_expected}.")
        print(f"[SUCCESS] All missing chunks re-indexed.")
        return True
