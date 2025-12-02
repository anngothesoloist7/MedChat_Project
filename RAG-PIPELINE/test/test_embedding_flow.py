import json
import os
import uuid
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from fastembed import SparseTextEmbedding

# Load env
load_dotenv()

def test_full_flow():
    print("--- Testing Full Embedding Flow (1 Batch) ---")
    
    # 1. Configuration
    GEMINI_API_KEY = os.getenv("GOOGLE_EMBEDDING_API_KEY")
    QDRANT_URL = os.getenv("SERVICE_URL_QDRANT")
    QDRANT_API_KEY = os.getenv("SERVICE_PASSWORD_QDRANTAPIKEY")
    COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "MedChat-RAG-v2")
    DENSE_VECTOR_SIZE = int(os.getenv("DENSE_VECTOR_SIZE", 1536))
    
    if not all([GEMINI_API_KEY, QDRANT_URL, QDRANT_API_KEY]):
        print("[ERROR] Missing API keys in .env")
        return

    # 2. Load Data
    parsed_dir = Path(os.getcwd()) / "database" / "parsed"
    chunk_files = list(parsed_dir.glob("*_chunks.json"))
    if not chunk_files: return print("[ERROR] No chunks found.")
    
    target_file = chunk_files[0]
    print(f"[INFO] Loading data from: {target_file.name}")
    with open(target_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    batch = chunks[:100]
    texts = [c['content'] for c in batch]
    print(f"[INFO] Processing {len(texts)} chunks.")

    # 3. Gemini Embedding (Dense)
    print("[INFO] Requesting Dense Embeddings from Gemini...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={GEMINI_API_KEY}"
    payload = {
        "requests": [{
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": t}]},
            "taskType": "RETRIEVAL_DOCUMENT",
            "outputDimensionality": DENSE_VECTOR_SIZE
        } for t in texts]
    }
    
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
        response.raise_for_status()
        embeddings = [e['values'] for e in response.json()['embeddings']]
        print(f"[SUCCESS] Received {len(embeddings)} dense vectors.")
    except Exception as e:
        return print(f"[ERROR] Gemini request failed: {e}")

    # 4. FastEmbed (Sparse)
    print("[INFO] Generating Sparse Vectors (BM25)...")
    sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
    sparse_vectors = list(sparse_model.embed(texts))
    print(f"[SUCCESS] Generated {len(sparse_vectors)} sparse vectors.")

    # 5. Create Points
    print("[INFO] Creating Qdrant Points...")
    points = []
    
    # Mock metadata for test
    book_meta = {"book_name": "Test Book", "author": "Test Author", "publish_year": "2024"}
    
    for j, chunk in enumerate(batch):
        text = chunk['content']
        sv = sparse_vectors[j]
        
        payload_data = {
            "text": text,
            "book_name": book_meta["book_name"],
            "author": book_meta["author"],
            "publish_year": book_meta["publish_year"],
            "page_number": chunk['metadata'].get('page_number', "Unknown"),
            "file_id": chunk['metadata'].get('file_id', "Unknown")
        }
        
        points.append(models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, text)),
            payload=payload_data,
            vector={
                "dense": embeddings[j],
                "bm25": models.SparseVector(
                    indices=sv.indices.tolist(),
                    values=sv.values.tolist()
                )
            }
        ))

    # Save Qdrant Payload
    qdrant_payload_file = "debug_qdrant_payload.json"
    print(f"[INFO] Saving Qdrant payload to {qdrant_payload_file}...")
    with open(qdrant_payload_file, 'w', encoding='utf-8') as f:
        # Convert PointStruct objects to dicts for JSON serialization
        points_dict = [p.dict() if hasattr(p, 'dict') else p.model_dump() for p in points]
        json.dump(points_dict, f, indent=2, ensure_ascii=False)

    # 6. Upsert to Qdrant
    print(f"[INFO] Upserting {len(points)} points to Qdrant collection '{COLLECTION_NAME}'...")
    client = QdrantClient(
        url=QDRANT_URL.rstrip('/'),
        port=443,
        https=True,
        api_key=QDRANT_API_KEY,
        timeout=60
    )
    
    try:
        client.upsert(COLLECTION_NAME, points=points, wait=True)
        print("[SUCCESS] Points upserted successfully!")
    except Exception as e:
        print(f"[ERROR] Upsert failed: {e}")

if __name__ == "__main__":
    test_full_flow()
