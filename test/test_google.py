import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

key = os.getenv("GOOGLE_API_KEY")
print(f"Testing Google API with key: {key[:5]}...")

client = genai.Client(api_key=key, http_options={'timeout': 120})

try:
    print("Embedding 'test'...")
    res = client.models.embed_content(
        model="gemini-embedding-001",
        contents=["test"],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    print("Success!")
    print(f"Embedding length: {len(res.embeddings[0].values)}")
except Exception as e:
    print(f"Error: {e}")
