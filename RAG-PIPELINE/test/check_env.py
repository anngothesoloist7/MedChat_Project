import os
import sys
from pathlib import Path
from modules.config import Config

def check_env():
    print(f"\n{'='*40}\nEnvironment Check\n{'='*40}")
    
    # 1. Check .env file
    env_path = Config.BASE_DIR / ".env"
    if env_path.exists():
        print(f"[OK] .env found at {env_path}")
    else:
        print(f"[FAIL] .env NOT found at {env_path}")
        return

    # 2. Check API Keys
    keys = [
        "MISTRAL_API_KEY",
        "GOOGLE_CHAT_API_KEY",
        "GOOGLE_EMBEDDING_API_KEY",
        "SERVICE_URL_QDRANT",
        "SERVICE_PASSWORD_QDRANTAPIKEY"
    ]
    
    missing = []
    for k in keys:
        val = os.getenv(k)
        if val and val.strip():
            print(f"[OK] {k} is set.")
        else:
            print(f"[FAIL] {k} is MISSING.")
            missing.append(k)
            
    if missing:
        print(f"\n[ERROR] Missing {len(missing)} required API keys.")
        return

    # 3. Check Directories
    dirs = [Config.RAW_DIR, Config.SPLITTED_DIR, Config.PARSED_DIR, Config.MODELS_DIR, Config.LOGS_DIR]
    for d in dirs:
        if d.exists():
            print(f"[OK] Directory exists: {d.name}")
        else:
            print(f"[WARN] Directory missing (will be created): {d.name}")

    # 4. Connectivity Check (Optional/Simple)
    print("\n[INFO] Testing Connectivity...")
    
    # Mistral
    try:
        from mistralai import Mistral
        client = Mistral(api_key=Config.MISTRAL_API_KEY)
        client.models.list()
        print("[OK] Mistral API connected.")
    except Exception as e:
        print(f"[FAIL] Mistral API failed: {e}")

    # Gemini
    try:
        from google import genai
        client = genai.Client(api_key=Config.GOOGLE_CHAT_API_KEY)
        client.models.get(model=Config.GEMINI_METADATA_MODEL)
        print("[OK] Gemini API connected.")
    except Exception as e:
        print(f"[FAIL] Gemini API failed: {e}")

    # Qdrant
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=Config.QDRANT_URL, api_key=Config.QDRANT_API_KEY)
        client.get_collections()
        print("[OK] Qdrant connected.")
    except Exception as e:
        print(f"[FAIL] Qdrant failed: {e}")

    print(f"\n{'='*40}\nCheck Complete\n{'='*40}")

if __name__ == "__main__":
    check_env()
