from modules.embedding_qdrant import QdrantManager
try:
    print("Initializing QdrantManager...")
    mgr = QdrantManager()
except Exception as e:
    print(f"QdrantManager init failed: {e}")

print("Importing google.genai...")
from google import genai
print("Import successful")
