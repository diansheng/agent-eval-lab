import numpy as np
import os
from .embedder import get_embedding
from .vector_store import VectorStore

class Retriever:
    def __init__(self, index_path: str = None, meta_path: str = None):
        """
        Initializes the retriever with a loaded VectorStore.
        """
        self.vector_store = VectorStore()
        
        # Determine paths relative to the app root if not provided
        if not index_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            index_path = os.path.join(base_dir, "data", "faiss.index")
        if not meta_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            meta_path = os.path.join(base_dir, "data", "metadata.json")
            
        self.index_path = index_path
        self.meta_path = meta_path
        
        # Load if they exist
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            self.vector_store.load(self.index_path, self.meta_path)
            
    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Searches the knowledge base for the most relevant chunks.
        """
        # Ensure we have data
        if not self.vector_store.metadata or self.vector_store.index.ntotal == 0:
            return []
            
        # 1. Embed the query
        query_embedding = get_embedding(query)
        
        # 2. Convert to numpy array shape (1, dimension)
        query_vector = np.array([query_embedding], dtype=np.float32)
        
        # 3. Search FAISS
        # D is the distances array, I is the indices array
        # We cap top_k to the number of total elements if it's smaller
        k = min(top_k, self.vector_store.index.ntotal)
        distances, indices = self.vector_store.index.search(query_vector, k)
        
        # 4. Map indices back to metadata
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1: # FAISS returns -1 if there aren't enough results
                continue
                
            chunk_data = self.vector_store.metadata[idx]
            results.append({
                "text": chunk_data["text"],
                "source": chunk_data["source"],
                "distance": float(distances[0][i]) # Add distance score for reference
            })
            
        return results
