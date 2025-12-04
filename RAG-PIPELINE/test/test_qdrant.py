from modules.embedding_qdrant import QdrantManager
import sys

try:
    print("Initializing QdrantManager...")
    manager = QdrantManager()
    print("Checking connection...")
    if manager.check_connections():
        print("Connection Successful!")
    else:
        print("Connection Failed!")
        sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
