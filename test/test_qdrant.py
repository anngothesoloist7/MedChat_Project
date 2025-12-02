import os
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, SparseVectorParams, Modifier

# Load environment variables
load_dotenv(Path(os.getcwd()) / ".env")

QDRANT_URL = os.getenv("SERVICE_URL_QDRANT", "https://qdrant.botnow.online/")
QDRANT_API_KEY = os.getenv("SERVICE_PASSWORD_QDRANTAPIKEY", None)
COLLECTION_NAME = "MedChat-RAG-v2"
DENSE_VECTOR_SIZE = 1536

import requests

print(f"Connecting to {QDRANT_URL}...")
headers = {"api-key": QDRANT_API_KEY} if QDRANT_API_KEY else {}

try:
    response = requests.get(f"{QDRANT_URL}/collections", headers=headers, timeout=10)
    print(f"Response status: {response.status_code}")
    print(f"Response text: {response.text}")
except Exception as e:
    print(f"Error: {e}")
