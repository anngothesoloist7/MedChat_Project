import os
import json
import uuid
import time
import requests
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from tqdm import tqdm
from fastembed import SparseTextEmbedding

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path if env_path.exists() else Path(os.getcwd()) / ".env")

class Config:
    BASE_DIR = Path(os.getcwd())
    GEMINI_API_KEY = os.getenv("GOOGLE_EMBEDDING_API_KEY")
    QDRANT_URL = os.getenv("SERVICE_URL_QDRANT")
    QDRANT_API_KEY = os.getenv("SERVICE_PASSWORD_QDRANTAPIKEY")
    COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "MedChat-RAG-v2")
    DENSE_VECTOR_SIZE = int(os.getenv("DENSE_VECTOR_SIZE", 1536))
    GEMINI_BATCH_SIZE = int(os.getenv("GEMINI_BATCH_SIZE", 100))
    QDRANT_BATCH_SIZE = int(os.getenv("QDRANT_BATCH_SIZE", 100))
    PARSED_FOLDER = BASE_DIR / "database" / "parsed"
    RAW_FOLDER = BASE_DIR / "database" / "raw"

class QdrantManager:
    def __init__(self):
        if not all([Config.QDRANT_URL, Config.QDRANT_API_KEY, Config.GEMINI_API_KEY]):
            raise ValueError("[ERROR] Missing required API keys in .env")
        
        if Config.QDRANT_API_KEY.startswith("AIza"):
            print("[WARN] Qdrant API Key looks like a Google Key. Check .env")
        
        self.qdrant_client = QdrantClient(
            url=Config.QDRANT_URL.rstrip('/'),
            port=443,
            https=True,
            api_key=Config.QDRANT_API_KEY,
            timeout=60,
            prefer_grpc=False,
        )
        # Initialize BM25 model for sparse vectors
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        
    def check_connections(self) -> bool:
        print("[INFO] Checking connections...")
        try:
            cols = self.qdrant_client.get_collections()
            print(f"[SUCCESS] Qdrant connected. Collections: {len(cols.collections)}")
            emb = self.get_embeddings_batch(["test"])
            print(f"[SUCCESS] Gemini connected. Embedding size: {len(emb[0])}")
            return True
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False

    def init_collection(self):
        if self.qdrant_client.collection_exists(Config.COLLECTION_NAME):
            print(f"[INFO] Collection {Config.COLLECTION_NAME} exists.")
            return

        print(f"[INFO] Creating collection: {Config.COLLECTION_NAME}")
        try:
            self.qdrant_client.create_collection(
                collection_name=Config.COLLECTION_NAME,
                vectors_config={"dense": models.VectorParams(size=Config.DENSE_VECTOR_SIZE, distance=models.Distance.COSINE)},
                sparse_vectors_config={"bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)}
            )
            print("[SUCCESS] Collection created.")
        except Exception as e:
            print(f"[ERROR] Failed to create collection: {e}")
            raise

    def get_embeddings_batch(self, texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={Config.GEMINI_API_KEY}"
        payload = {
            "requests": [{
                "model": "models/gemini-embedding-001",
                "content": {"parts": [{"text": t}]},
                "taskType": task_type,
                "outputDimensionality": Config.DENSE_VECTOR_SIZE
            } for t in texts]
        }
        
        for attempt in range(5):
            try:
                res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
                res.raise_for_status()
                return [e['values'] for e in res.json()['embeddings']]
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    print(f"[WARN] Rate limit hit (429). Sleeping 30s... (Attempt {attempt+1}/5)")
                    time.sleep(30)
                    continue
                if attempt == 4: raise
                time.sleep(2 ** attempt)
            except Exception as e:
                if attempt == 4: raise
                time.sleep(2 ** attempt)
        return []

    def load_metadata(self, book_name: str) -> Dict[str, Any]:
        import re
        base_name = re.sub(r'\(\d+(-\d+)?\)$', '', book_name).strip()
        path = Config.RAW_FOLDER / f"{base_name}_metadata.json"
        
        meta = {}
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f: 
                    meta = json.load(f)
            except Exception: pass
            
        # Ensure book_name is set, defaulting to filename if missing in JSON
        if not any(k in meta for k in ["book_name", "BOOK_NAME", "Title", "TITLE"]):
            meta["book_name"] = base_name
            
        return meta

    def process_batch(self, batch: List[Dict], book_meta: Dict[str, Any], batch_index: int):
        """Processes a single batch: Embed -> Create Points -> Upsert"""
        try:
            # 1. Embed
            texts = [c['content'] for c in batch]
            embeddings = self.get_embeddings_batch(texts)
            
            # Generate Sparse Vectors (BM25)
            # fastembed returns a generator, convert to list
            sparse_vectors = list(self.sparse_model.embed(texts))
            
            # 2. Create Points
            points = []
            for j, chunk in enumerate(batch):
                text = chunk['content']
                
                # Resolve metadata with fallbacks
                b_name = book_meta.get("book_name") or book_meta.get("BOOK_NAME") or book_meta.get("Title") or "Unknown"
                author = book_meta.get("author") or book_meta.get("AUTHOR") or "Unknown"
                year = book_meta.get("publish_year") or book_meta.get("PUBLISH YEAR") or "Unknown"
                keywords = book_meta.get("keywords") or book_meta.get("KEYWORDS") or []
                lang = book_meta.get("language") or book_meta.get("LANGUAGE") or "Unknown"
                page_num = chunk['metadata'].get('page_number', chunk['metadata'].get('page', "Unknown"))
                
                payload = {
                    "text": text,
                    "book_name": b_name,
                    "author": author,
                    "publish_year": year,
                    "keywords": keywords,
                    "language": lang,
                    "page_number": page_num
                }
                
                # Convert sparse vector to Qdrant format
                sv = sparse_vectors[j]
                points.append(models.PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_DNS, text)),
                    payload=payload,
                    vector={
                        "dense": embeddings[j],
                        "bm25": models.SparseVector(
                            indices=sv.indices.tolist(),
                            values=sv.values.tolist()
                        )
                    }
                ))
            
            # 3. Upsert
            if points:
                self.qdrant_client.upsert(Config.COLLECTION_NAME, points=points, wait=True)
            return len(batch)
            
        except Exception as e:
            print(f"[ERROR] Batch {batch_index} failed: {e}")
            return 0

    def process_and_index(self, json_path: str):
        path = Path(json_path)
        if not path.exists(): return print(f"[ERROR] File not found: {json_path}")

        print(f"\n[INFO] Processing: {path.name}")
        with open(path, 'r', encoding='utf-8') as f: chunks = json.load(f)
        if not chunks: return print("[WARN] No chunks found.")

        book_meta = self.load_metadata(path.stem.replace("_chunks", ""))
        total = len(chunks)
        print(f"[INFO] Indexing {total:,} chunks (Batch: {Config.GEMINI_BATCH_SIZE})...")
        
        start = time.time()
        
        with tqdm(total=total, desc="Indexing", unit="chunk") as pbar:
            for i in range(0, total, Config.GEMINI_BATCH_SIZE):
                batch = chunks[i : i + Config.GEMINI_BATCH_SIZE]
                processed_count = self.process_batch(batch, book_meta, i // Config.GEMINI_BATCH_SIZE)
                pbar.update(processed_count)
            
        print(f"[SUCCESS] Finished in {(time.time() - start)/60:.1f} min")

def run_embedding(files: List[str]):
    manager = QdrantManager()
    if not manager.check_connections(): return
    manager.init_collection()
    
    for f in files:
        path = Path(f)
        target = Config.PARSED_FOLDER / f"{path.stem}_chunks.json" if path.suffix.lower() == '.pdf' else path
        if target.exists(): manager.process_and_index(str(target))
        else: print(f"[WARN] Chunks not found: {path.name}")
