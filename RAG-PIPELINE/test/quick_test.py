"""Quick test for embedding_qdrant_v2 module"""

from modules.embedding_qdrant_v2 import QdrantManager

print("=" * 60)
print("Testing Embedding Module V2")
print("=" * 60)

try:
    manager = QdrantManager()
    print("[✓] QdrantManager initialized successfully")
    
    # Test connections
    print("\n[INFO] Testing connections...")
    if manager.check_connections():
        print("[✓] All connections working!")
        
        # Test collection
        print("\n[INFO] Testing collection creation...")
        manager.init_collection()
        print("[✓] Collection ready!")
        
        # Test small batch
        print("\n[INFO] Testing small batch embedding...")
        test_texts = [
            "Aspirin is a medication.",
            "Paracetamol treats pain.",
            "Ibuprofen reduces inflammation."
        ]
        embeddings = manager.get_embeddings_batch(test_texts)
        print(f"[✓] Generated {len(embeddings)} embeddings")
        print(f"    Dimension: {len(embeddings[0])}")
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nReady to run:")
        print('  uv run python main.py "path/to/pdf" --phase 3')
        
    else:
        print("[✗] Connection test failed")
        
except Exception as e:
    print(f"\n[✗] Error: {e}")
    import traceback
    traceback.print_exc()
