import sys
import os
import json
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag.embedder import get_embeddings_batch
from rag.vector_store import VectorStore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def build_db_clean():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(base_dir, "../scripts/dataset_builder/output_clean/rag_dataset.jsonl")
    index_path = os.path.join(base_dir, "data/vector_store_clean/index.faiss")
    meta_path = os.path.join(base_dir, "data/vector_store_clean/metadata.json")
    
    # Ensure destination directory exists
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    
    if not os.path.exists(dataset_path):
        logging.error(f"Clean dataset not found at {dataset_path}")
        return
        
    chunks = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
                
    logging.info(f"Loaded {len(chunks)} chunks from clean dataset.")
    
    texts = [chunk["content"] for chunk in chunks]
    
    batch_size = 10
    all_embeddings = []
    
    try:
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            logging.info(f"Getting embeddings for batch {i//batch_size + 1} of clean data...")
            embeddings = get_embeddings_batch(batch_texts)
            all_embeddings.extend(embeddings)
    except Exception as e:
        logging.error(f"Failed to get embeddings: {e}")
        return
        
    if len(all_embeddings) > 0:
        dim = len(all_embeddings[0])
        logging.info(f"Embedding dimension is {dim}")
    else:
        logging.error("No embeddings generated.")
        return
        
    vs = VectorStore(dimension=dim)
    vs.add_documents(chunks, all_embeddings)
    
    vs.save(index_path, meta_path)
    logging.info(f"Successfully saved Clean Vector DB to {index_path} and {meta_path}")

if __name__ == "__main__":
    build_db_clean()
