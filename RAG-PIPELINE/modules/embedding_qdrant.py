import os
import json
import uuid
import time
import requests
from typing import List, Dict, Any
from pathlib import Path
from qdrant_client import QdrantClient, models
from tqdm import tqdm
from fastembed import SparseTextEmbedding
from modules.utils.pipeline_logger import pipeline_logger
from modules.config import Config

class QdrantManager:
    def __init__(self):
        if not all([Config.QDRANT_URL, Config.QDRANT_API_KEY, Config.GOOGLE_EMBEDDING_API_KEY]):
            raise ValueError("[ERROR] Missing required API keys in .env")
        
        if Config.QDRANT_API_KEY.startswith("AIza"):
            raise ValueError("[ERROR] QDRANT_API_KEY looks like a Google API Key.")

        self.qdrant_client = QdrantClient(url=Config.QDRANT_URL, port=443, api_key=Config.QDRANT_API_KEY)
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25", cache_dir=str(Config.MODELS_DIR))
        self.Config = Config

    def check_connections(self) -> bool:
        try:
            self.qdrant_client.get_collections()
            print("[SUCCESS] Qdrant connected.")
            return True
        except Exception as e:
            print(f"[ERROR] Qdrant connection failed: {e}")
            return False

    def init_collection(self):
        if not self.qdrant_client.collection_exists(Config.COLLECTION_NAME):
            print(f"[INFO] Creating collection: {Config.COLLECTION_NAME}")
            self.qdrant_client.create_collection(
                collection_name=Config.COLLECTION_NAME,
                vectors_config={"dense": models.VectorParams(size=Config.DENSE_VECTOR_SIZE, distance=models.Distance.COSINE)},
                sparse_vectors_config={"bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)}
            )
        else:
            print(f"[INFO] Collection {Config.COLLECTION_NAME} exists.")

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={Config.GOOGLE_EMBEDDING_API_KEY}"
        payload = {
            "requests": [{
                "model": "models/gemini-embedding-001",
                "content": {"parts": [{"text": t}]},
                "taskType": "RETRIEVAL_DOCUMENT",
                "outputDimensionality": Config.DENSE_VECTOR_SIZE
            } for t in texts]
        }
        
        for attempt in range(5):
            try:
                response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
                if response.status_code == 200:
                    return [e['values'] for e in response.json().get('embeddings', [])]
                if response.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                print(f"[ERROR] Embedding API Error: {response.text}")
                return []
            except Exception as e:
                print(f"[ERROR] Embedding Request Failed: {e}")
                time.sleep(1)
        return []

    def generate_id(self, book_name: str, page: int, content: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{book_name}_{page}_{content[:50]}"))

    def load_metadata(self, book_name: str) -> Dict[str, Any]:
        import re
        base_name = re.sub(r'\(\d+(-\d+)?\)$', '', book_name).strip()
        path = Config.RAW_DIR / f"{base_name}_metadata.json"
        meta = {}
        if path.exists():
            try: meta = json.loads(path.read_text(encoding="utf-8"))
            except: pass
        return {
            "book_name": meta.get("book_name") or meta.get("BOOK_NAME") or meta.get("Title") or book_name,
            "author": meta.get("author") or meta.get("AUTHOR") or "Unknown",
            "publish_year": meta.get("publish_year") or meta.get("PUBLISH_YEAR") or "Unknown",
            "keywords": meta.get("keywords") or meta.get("KEYWORDS") or [],
            "language": meta.get("language") or meta.get("LANGUAGE") or "Unknown",
            "pdf_id": meta.get("pdf_id", "unknown")
        }

    def process_batch(self, batch: List[Dict], book_meta: Dict, batch_id: str) -> int:
        if not batch: return 0
        texts = [item['content'] for item in batch]
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        if not valid_indices: return 0
        
        valid_texts = [texts[i] for i in valid_indices]
        try: embeddings_valid = self.get_embeddings_batch(valid_texts)
        except Exception as e:
            print(f"[ERROR] Embedding failed for batch {batch_id}: {e}")
            return 0

        embeddings = [None] * len(batch)
        for i, valid_idx in enumerate(valid_indices): embeddings[valid_idx] = embeddings_valid[i]
        sparse_vectors = list(self.sparse_model.embed(texts))

        points = []
        for i, item in enumerate(batch):
            if embeddings[i] is None: continue
            
            point_id = self.generate_id(book_meta["book_name"], item['metadata'].get('page_number', 0), item['content'])
            payload = {
                "text": item['content'], "metadata": item['metadata'], **book_meta
            }
            
            points.append(models.PointStruct(
                id=point_id,
                vector={"dense": embeddings[i], "bm25": models.SparseVector(indices=sparse_vectors[i].indices.tolist(), values=sparse_vectors[i].values.tolist())},
                payload=payload
            ))

        try:
            self.qdrant_client.upsert(collection_name=Config.COLLECTION_NAME, points=points)
            return len(points)
        except Exception as e:
            print(f"[ERROR] Upsert failed for batch {batch_id}: {e}")
            return 0

    def process_and_index(self, json_path: str, overwrite: bool = False):
        with open(json_path, 'r', encoding='utf-8') as f: chunks = json.load(f)
        if not chunks: return

        book_name = Path(json_path).stem.replace("_chunks", "")
        book_meta = self.load_metadata(book_name)
        pdf_id = book_meta.get("pdf_id")

        if pdf_id and pdf_id != "unknown":
            try:
                count_res = self.qdrant_client.count(
                    collection_name=Config.COLLECTION_NAME,
                    count_filter=models.Filter(must=[models.FieldCondition(key="pdf_id", match=models.MatchValue(value=pdf_id))])
                )
                if count_res.count > 0:
                    if overwrite:
                        print(f"[INFO] Overwriting {book_name} (PDF ID: {pdf_id}). Deleting {count_res.count} existing points...")
                        self.qdrant_client.delete(
                            collection_name=Config.COLLECTION_NAME,
                            points_selector=models.FilterSelector(
                                filter=models.Filter(must=[models.FieldCondition(key="pdf_id", match=models.MatchValue(value=pdf_id))])
                            )
                        )
                        print("[SUCCESS] Deleted existing points.")
                    else:
                        print(f"[WARN] {book_name} already exists in Qdrant ({count_res.count} points). Skipping (overwrite=False).")
                        return
            except Exception as e:
                print(f"[WARN] Failed to check/delete existing points for {book_name}: {e}")

        print(f"[INFO] Indexing {len(chunks)} chunks for {book_name}...")
        
        # Get collection size before
        try:
            info_before = self.qdrant_client.get_collection(Config.COLLECTION_NAME)
            size_before = info_before.points_count
        except: size_before = 0
        
        total_indexed = 0
        batch_size = Config.GEMINI_BATCH_SIZE
        
        for i in tqdm(range(0, len(chunks), batch_size), desc="Indexing"):
            batch = chunks[i : i + batch_size]
            total_indexed += self.process_batch(batch, book_meta, f"{i//batch_size}")
            time.sleep(0.5) 
            
        # Get collection size after
        try:
            info_after = self.qdrant_client.get_collection(Config.COLLECTION_NAME)
            size_after = info_after.points_count
        except: size_after = 0

        pipeline_logger.log_phase_3(
            book_name=book_name, 
            total_chunks=len(chunks), 
            imported=total_indexed, 
            failed=len(chunks) - total_indexed,
            collection_size_before=size_before,
            collection_size_after=size_after
        )

def run_embedding(files: list[str], overwrite: bool = False):
    manager = QdrantManager()
    if not manager.check_connections(): return
    manager.init_collection()
    
    processed_files = []
    for f in files:
        path = Path(f)
        target = Config.PARSED_DIR / f"{path.stem}_chunks.json" if path.suffix.lower() == '.pdf' else path
        if target.exists(): 
            manager.process_and_index(str(target), overwrite=overwrite)
            processed_files.append(str(target))
        else:
            print(f"[WARN] Parsed file not found: {target}")
            
    from modules.utils.qdrant_verifier import verify_and_retry_indexing
    verify_and_retry_indexing(manager, processed_files)
