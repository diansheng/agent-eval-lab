import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.document_processor import process_directory
from app.rag.embedder import get_embeddings_batch
from app.rag.vector_store import VectorStore
from app.rag.retriever import Retriever

def build_index():
    print("Loading and chunking documents...")
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "knowledge_base")
    chunks = process_directory(docs_dir)
    print(f"Created {len(chunks)} chunks.")
    
    if not chunks:
        print("No documents found to index.")
        return

    print("Generating embeddings (this may take a moment)...")
    texts = [c["text"] for c in chunks]
    embeddings = get_embeddings_batch(texts)
    
    print("Building FAISS index...")
    # Get dimension from the first embedding
    dimension = len(embeddings[0])
    store = VectorStore(dimension=dimension)
    store.add_documents(chunks, embeddings)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_path = os.path.join(base_dir, "data", "faiss.index")
    meta_path = os.path.join(base_dir, "data", "metadata.json")
    
    print(f"Saving index to {index_path}...")
    store.save(index_path, meta_path)
    print("Done building index!")

def test_search(query: str):
    print(f"\n--- Testing Query: '{query}' ---")
    retriever = Retriever()
    results = retriever.search(query, top_k=2)
    
    for i, res in enumerate(results, 1):
        print(f"\nResult {i} (Source: {res['source']}, Distance: {res['distance']:.4f}):")
        print("-" * 40)
        print(res['text'][:300] + "..." if len(res['text']) > 300 else res['text'])
        print("-" * 40)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check if MINIMAX_API_KEY is set
    if not os.environ.get("MINIMAX_API_KEY"):
        print("WARNING: MINIMAX_API_KEY is not set. The embedding generation will likely fail.")
        
    print("Choose an action:")
    print("1) Build Vector Index")
    print("2) Test Search")
    print("3) Build and Test")
    
    choice = input("> ")
    
    if choice in ["1", "3"]:
        build_index()
        
    if choice in ["2", "3"]:
        test_search("Has this bug happened before?")
        test_search("Where is authentication implemented?")
