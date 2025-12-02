import httpx
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SERVICE_URL_QDRANT")
key = os.getenv("SERVICE_PASSWORD_QDRANTAPIKEY")

print(f"Testing connection to {url}...")

try:
    headers = {"api-key": key}
    resp = httpx.get(f"{url}/collections", headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
