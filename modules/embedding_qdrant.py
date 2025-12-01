import os
import json
import uuid
import time
import requests
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import VectorParams, Distance, SparseVectorParams, Modifier
from fastembed import SparseTextEmbedding

# Load environment variables
load_dotenv(Path(os.getcwd()) / ".env")

class Config:
    BASE_DIR = Path(os.getcwd())
    GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
    QDRANT_URL = os.getenv("SERVICE_URL_QDRANT")
    QDRANT_API_KEY = os.getenv("SERVICE_PASSWORD_QDRANTAPIKEY")
    COLLECTION_NAME = "MedChat-RAG"
    DENSE_VECTOR_SIZE = 1536 
    
    # Batching & Rate Limits (Gemini Free Tier)
    BATCH_SIZE = 20 # Reduced batch size to stay safe with tokens
    RPM_LIMIT = 100
    TPM_LIMIT = 30000
    
    PARSED_FOLDER = BASE_DIR / "database" / "parsed"
    RAW_FOLDER = BASE_DIR / "database" / "raw"

class QdrantManager:
    def __init__(self):
        self.client = QdrantClient(url=Config.QDRANT_URL, api_key=Config.QDRANT_API_KEY)
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        
        # Rate Limiting State
        self.last_request_time = 0
        self.tokens_used_minute = 0
        self.minute_start_time = time.time()

    def check_connections(self) -> bool:
        """Checks connections to Qdrant and Gemini API."""
        print("[INFO] Checking connections...")
        
        # 1. Check Qdrant
        try:
            self.client.get_collections()
            print("[SUCCESS] Qdrant connected.")
        except Exception as e:
            print(f"[ERROR] Qdrant connection failed: {e}")
            return False

        # 2. Check Gemini
        try:
            # Simple dummy embedding
            self.get_gemini_embedding_single("test")
            print("[SUCCESS] Gemini API connected.")
        except Exception as e:
            print(f"[ERROR] Gemini API check failed: {e}")
            return False
            
        return True

    def init_collection(self):
        """Initializes the Qdrant collection if it doesn't exist."""
        if not self.client.collection_exists(Config.COLLECTION_NAME):
            print(f"[INFO] Creating collection: {Config.COLLECTION_NAME}")
            self.client.create_collection(
                collection_name=Config.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=Config.DENSE_VECTOR_SIZE,
                    distance=Distance.COSINE
                ),
                sparse_vectors_config={
                    "bm25": SparseVectorParams(modifier=Modifier.IDF)
                }
            )
            print("[SUCCESS] Collection created.")
        else:
            print(f"[INFO] Collection {Config.COLLECTION_NAME} already exists.")

    def _wait_for_rate_limit(self, estimated_tokens: int):
        """Enforces RPM and TPM limits."""
        current_time = time.time()
        
        # Reset minute counter if window passed
        if current_time - self.minute_start_time >= 60:
            self.minute_start_time = current_time
            self.tokens_used_minute = 0
        
        # Check TPM (Tokens Per Minute)
        if self.tokens_used_minute + estimated_tokens > Config.TPM_LIMIT:
            wait_time = 60 - (current_time - self.minute_start_time) + 1
            print(f"[WARN] Token limit reached ({self.tokens_used_minute}/{Config.TPM_LIMIT}). Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            self.minute_start_time = time.time()
            self.tokens_used_minute = 0
            
        # Check RPM (Requests Per Minute) - Enforce min interval
        # 100 RPM = 0.6s interval. Using 1.0s to be safe.
        time_since_last = current_time - self.last_request_time
        if time_since_last < 1.0:
            time.sleep(1.0 - time_since_last)
            
        self.last_request_time = time.time()
        self.tokens_used_minute += estimated_tokens

    def get_gemini_embedding_single(self, text: str) -> List[float]:
        """Helper for single embedding (used in connection check)."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={Config.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_DOCUMENT",
            "outputDimensionality": Config.DENSE_VECTOR_SIZE 
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()['embedding']['values']

    def get_gemini_embeddings_batched(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of texts using Gemini API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={Config.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        
        # Estimate tokens (char count / 4)
        total_chars = sum(len(t) for t in texts)
        estimated_tokens = int(total_chars / 4)
        
        self._wait_for_rate_limit(estimated_tokens)
        
        payload = {
            "requests": [
                {
                    "model": "models/gemini-embedding-001",
                    "content": {"parts": [{"text": t}]},
                    "taskType": "RETRIEVAL_DOCUMENT",
                    "outputDimensionality": Config.DENSE_VECTOR_SIZE
                } for t in texts
            ]
        }
        
        retries = 3
        for attempt in range(retries):
            try:
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()
                # Parse batched response
                return [e['values'] for e in response.json()['embeddings']]
            except Exception as e:
                if "429" in str(e):
                    wait_time = 2 ** (attempt + 1)
                    print(f"[WARN] Rate limit hit (429). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"[ERROR] Batch embedding failed: {e}")
                    return []
        return []

    def generate_deterministic_id(self, text: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, text))

    def load_metadata(self, book_name: str) -> Dict[str, Any]:
        import re
        base_name = re.sub(r'\(\d+-\d+\)$', '', book_name).strip()
        base_name = re.sub(r'\(\d+\)$', '', base_name).strip()
        
        metadata_path = Config.RAW_FOLDER / f"{base_name}_metadata.json"
        
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load metadata: {e}")
        return {}

    def process_and_index(self, json_path: str):
        path = Path(json_path)
        if not path.exists():
            print(f"[ERROR] File not found: {json_path}")
            return

        print(f"\n[INFO] Processing chunks from: {path.name}")
        
        with open(path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
            
        if not chunks:
            print("[WARN] No chunks found.")
            return

        # Load Metadata
        book_name_from_file = path.stem.replace("_chunks", "")
        book_metadata = self.load_metadata(book_name_from_file)
        
        total_chunks = len(chunks)
        print(f"[INFO] Indexing {total_chunks} chunks (Batch Size: {Config.BATCH_SIZE})...")
        
        points_to_upsert = []
        
        for i in range(0, total_chunks, Config.BATCH_SIZE):
            batch = chunks[i : i + Config.BATCH_SIZE]
            batch_texts = [c['content'] for c in batch]
            
            # 1. Sparse Embeddings
            try:
                sparse_embeddings = list(self.sparse_model.embed(batch_texts))
            except Exception as e:
                print(f"[ERROR] Sparse embedding failed: {e}")
                continue

            # 2. Dense Embeddings (Batched)
            dense_embeddings = self.get_gemini_embeddings_batched(batch_texts)
            if not dense_embeddings or len(dense_embeddings) != len(batch):
                print(f"[WARN] Skipping batch {i}: Dense embedding failed or mismatch.")
                continue
            
            # 3. Create Points
            for j, chunk in enumerate(batch):
                text = chunk['content']
                point_id = self.generate_deterministic_id(text)
                
                payload = {
                    "text": text,
                    "book_name": book_metadata.get("book_name", book_name_from_file),
                    "author": book_metadata.get("author", "Unknown"),
                    "publish_year": book_metadata.get("publish_year", "Unknown"),
                    "keywords": book_metadata.get("keywords", []),
                    "language": book_metadata.get("language", "Unknown"),
                    "page": chunk['metadata'].get('page', 0),
                    "chunk_index": chunk['metadata'].get('chunk_index', 0),
                    "source_file": chunk['metadata'].get('source', "")
                }
                
                point = models.PointStruct(
                    id=point_id,
                    payload=payload,
                    vector={
                        "": dense_embeddings[j],
                        "bm25": models.SparseVector(
                            indices=sparse_embeddings[j].indices.tolist(),
                            values=sparse_embeddings[j].values.tolist()
                        )
                    }
                )
                points_to_upsert.append(point)
            
            # 4. Upsert Batch
            if points_to_upsert:
                try:
                    self.client.upsert(
                        collection_name=Config.COLLECTION_NAME,
                        points=points_to_upsert
                    )
                    print(f"[INFO] Indexed batch {i // Config.BATCH_SIZE + 1}/{total_chunks // Config.BATCH_SIZE + 1}")
                except Exception as e:
                    print(f"[ERROR] Batch upsert failed: {e}")
                finally:
                    points_to_upsert = []

        print(f"[SUCCESS] Finished indexing {path.name}")

def run_embedding(files: List[str]):
    if not Config.GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY not set.")
        return

    manager = QdrantManager()
    
    # Pre-flight checks
    if not manager.check_connections():
        print("[ERROR] Connection checks failed. Aborting.")
        return
        
    manager.init_collection()
    
    for file_path in files:
        path = Path(file_path)
        target_json = path
        if path.suffix.lower() == '.pdf':
             target_json = Config.PARSED_FOLDER / f"{path.stem}_chunks.json"
        
        if target_json.exists():
            manager.process_and_index(str(target_json))
        else:
            print(f"[WARN] JSON chunks not found for: {path.name}")
