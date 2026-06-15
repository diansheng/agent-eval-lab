import faiss
import numpy as np
import json
import os

class VectorStore:
    def __init__(self, dimension: int = 1536):
        """
        Initializes a FAISS index for L2 distance.
        dimension: 1536 is the default for text-embedding-3-small.
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata = []

    def add_documents(self, chunks: list[dict], embeddings: list[list[float]]):
        """
        Adds chunks and their corresponding embeddings to the store.
        """
        if not chunks or not embeddings:
            return
            
        if len(chunks) != len(embeddings):
            raise ValueError("The number of chunks must match the number of embeddings.")
            
        # Convert list of embeddings to a float32 numpy array as required by FAISS
        numpy_embeddings = np.array(embeddings, dtype=np.float32)
        
        # Add vectors to the FAISS index
        self.index.add(numpy_embeddings)
        
        # Store metadata in the exact same order
        self.metadata.extend(chunks)

    def save(self, index_path: str, meta_path: str):
        """
        Saves the FAISS index and metadata to disk.
        """
        # Ensure directories exist
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        os.makedirs(os.path.dirname(meta_path), exist_ok=True)
        
        faiss.write_index(self.index, index_path)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

    def load(self, index_path: str, meta_path: str):
        """
        Loads the FAISS index and metadata from disk.
        """
        if not os.path.exists(index_path) or not os.path.exists(meta_path):
            raise FileNotFoundError("Index or metadata file not found.")
            
        self.index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)
            
        self.dimension = self.index.d
