import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_EMBEDDING_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={api_key}"
payload = {"requests": [{"model": "models/gemini-embedding-001", "content": {"parts": [{"text": "Hello world"}]}}]}

try:
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    if response.status_code == 200:
        embeddings = [e['values'] for e in response.json().get('embeddings', [])]
        if embeddings:
            print(f"Vector dimension: {len(embeddings[0])}")
        else:
            print("No embeddings returned")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
