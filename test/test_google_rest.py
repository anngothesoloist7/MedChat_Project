import requests
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GOOGLE_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={key}"

payload = {
    "content": {"parts": [{"text": "test"}]},
    "taskType": "RETRIEVAL_DOCUMENT"
}

print(f"Testing Google REST API...")
try:
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    print("Success!")
    print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
