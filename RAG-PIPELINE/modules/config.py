import os
from pathlib import Path
from dotenv import load_dotenv

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent # rag-pipeline

# Load .env from rag-pipeline root
load_dotenv(BASE_DIR / ".env")

class Config:
    # Paths
    BASE_DIR = BASE_DIR
    PIPELINE_ROOT = BASE_DIR
    RAW_DIR = PIPELINE_ROOT / "database" / "raw"
    SPLITTED_DIR = PIPELINE_ROOT / "database" / "splitted"
    PARSED_DIR = PIPELINE_ROOT / "database" / "parsed"
    MODELS_DIR = PIPELINE_ROOT / "models"
    LOGS_DIR = PIPELINE_ROOT / "logs"

    # Ensure directories exist
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SPLITTED_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # API Keys
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    GOOGLE_CHAT_API_KEY = os.getenv("GOOGLE_CHAT_API_KEY")
    GOOGLE_EMBEDDING_API_KEY = os.getenv("GOOGLE_EMBEDDING_API_KEY")
    QDRANT_URL = os.getenv("SERVICE_URL_QDRANT")
    QDRANT_API_KEY = os.getenv("SERVICE_PASSWORD_QDRANTAPIKEY")

    # Models & Settings
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-ocr-latest")
    GEMINI_METADATA_MODEL = os.getenv("GEMINI_METADATA_MODEL", "gemini-pro-latest")
    GEMINI_TRANSLATOR_MODEL = os.getenv("GEMINI_TRANSLATOR_MODEL", "gemini-2.5-flash")
    GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"
    
    # Qdrant
    COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "MedChat-RAG-v2")
    DENSE_VECTOR_SIZE = int(os.getenv("DENSE_VECTOR_SIZE", 1536))
    QDRANT_BATCH_SIZE = int(os.getenv("QDRANT_BATCH_SIZE", 100))
    GEMINI_BATCH_SIZE = int(os.getenv("GEMINI_BATCH_SIZE", 100))

    # Processing
    TARGET_CHUNK_SIZE = int(os.getenv('TARGET_CHUNK_SIZE_MB', 50)) * 1024 * 1024
    MAX_PAGES = int(os.getenv('MAX_PAGES', 500))
    MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", 20))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
