"""
setup_kb.py — Initialize the ChromaDB knowledge base from local text files.
Run once before starting the app, or call initialize_kb() programmatically.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

KB_DIR = os.path.join(os.path.dirname(__file__), "data", "knowledge_base")

FILES = {
    "manuals":         "equipment_manuals.txt",
    "sops":            "maintenance_sops.txt",
    "spare_parts":     "spare_parts.txt",
    "failure_reports": "failure_reports.txt",
}


def initialize_kb(rag=None):
    """Load all knowledge base documents into ChromaDB."""
    if rag is None:
        from backend.rag_pipeline import RAGPipeline
        rag = RAGPipeline()

    if not rag.is_available():
        print("[KB] ChromaDB not available — skipping initialization.")
        return False

    total = 0
    for collection, filename in FILES.items():
        filepath = os.path.join(KB_DIR, filename)
        if not os.path.exists(filepath):
            print(f"[KB] File not found: {filepath}")
            continue
        n = rag.ingest_file(filepath, collection, doc_id=filename.replace(".txt", ""))
        print(f"[KB] {collection}: {n} chunks loaded from {filename}")
        total += n

    print(f"[KB] Total: {total} chunks loaded into ChromaDB.")
    return True


if __name__ == "__main__":
    print("Initializing SteelGuard AI Knowledge Base...")
    success = initialize_kb()
    if success:
        print("✅ Knowledge base ready.")
    else:
        print("❌ Initialization failed — check ChromaDB installation.")
