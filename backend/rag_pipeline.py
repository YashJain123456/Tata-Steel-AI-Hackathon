import os
from typing import List

import sys
if "linux" in sys.platform:
    import pysqlite3
    sys.modules['sqlite3'] = pysqlite3

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

KB_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chromadb")
COLLECTIONS = ["manuals", "sops", "spare_parts", "failure_reports"]


class RAGPipeline:
    def __init__(self):
        os.makedirs(CHROMA_DIR, exist_ok=True)
        try:
            self.ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            self.client = chromadb.PersistentClient(path=CHROMA_DIR)
            self.cols = {
                name: self.client.get_or_create_collection(name=name, embedding_function=self.ef)
                for name in COLLECTIONS
            }
            self._available = True
        except Exception as e:
            print(f"[RAG] ChromaDB init failed: {e}")
            import streamlit as st
            st.error(f"ChromaDB init failed: {str(e)}")
            self._available = False
            self.cols = {}

    def is_available(self) -> bool:
        return self._available

    def ingest_file(self, filepath: str, collection: str, doc_id: str) -> int:
        if not self._available or collection not in self.cols:
            return 0
        if not os.path.exists(filepath):
            return 0
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = self._chunk(text)
        ids   = [f"{doc_id}__{i}" for i in range(len(chunks))]
        metas = [{"source": os.path.basename(filepath), "chunk": i} for i in range(len(chunks))]
        existing = set(self.cols[collection].get(ids=ids)["ids"])
        new_ids, new_docs, new_metas = [], [], []
        for cid, chunk, meta in zip(ids, chunks, metas):
            if cid not in existing:
                new_ids.append(cid); new_docs.append(chunk); new_metas.append(meta)
        if new_ids:
            self.cols[collection].add(documents=new_docs, ids=new_ids, metadatas=new_metas)
        return len(chunks)

    def ingest_text(self, text: str, collection: str, doc_id: str, metadata: dict = {}) -> int:
        if not self._available or collection not in self.cols:
            return 0
        chunks = self._chunk(text)
        ids   = [f"{doc_id}__{i}" for i in range(len(chunks))]
        metas = [{**metadata, "chunk": i} for i in range(len(chunks))]
        existing = set(self.cols[collection].get(ids=ids)["ids"])
        new_ids  = [i for i in ids if i not in existing]
        new_docs = [chunks[ids.index(i)] for i in new_ids]
        new_metas = [metas[ids.index(i)] for i in new_ids]
        if new_ids:
            self.cols[collection].add(documents=new_docs, ids=new_ids, metadatas=new_metas)
        return len(chunks)

    def query(self, query_text: str, n_results: int = 5, collection: str | None = None) -> str:
        if not self._available:
            return ""
        results: List[str] = []
        cols_to_search = (
            [self.cols[collection]]
            if collection and collection in self.cols
            else list(self.cols.values())
        )
        for col in cols_to_search:
            try:
                count = col.count()
                if count == 0:
                    continue
                res  = col.query(query_texts=[query_text], n_results=min(n_results, count))
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                for doc, meta in zip(docs, metas):
                    source = meta.get("source", "knowledge base")
                    results.append(f"[Source: {source}]\n{doc}")
            except Exception:
                continue
        return "\n\n---\n\n".join(results[:n_results])

    def get_stats(self) -> dict:
        if not self._available:
            return {c: 0 for c in COLLECTIONS}
        return {name: col.count() for name, col in self.cols.items()}

    def is_populated(self) -> bool:
        if not self._available:
            return False
        return any(col.count() > 0 for col in self.cols.values())

    @staticmethod
    def _chunk(text: str, size: int = 400, overlap: int = 40) -> List[str]:
        words  = text.split()
        chunks = []
        step   = size - overlap
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + size])
            if chunk.strip():
                chunks.append(chunk)
        return chunks if chunks else [text]
