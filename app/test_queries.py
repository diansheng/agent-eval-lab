import sys
import os
import json
import logging

# Ensure we can import from the app folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag.retriever import Retriever

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def test_retrieval(version="v1"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, f"../data/{version}/vector_store/index.faiss")
    meta_path = os.path.join(base_dir, f"../data/{version}/vector_store/metadata.json")
    
    logging.info("Initializing Retriever...")
    retriever = Retriever(index_path=index_path, meta_path=meta_path)
    
    test_queries = [
        "What are the progressive property tax rates for owner-occupied residential properties?",
        "Can I use my CPF Ordinary Account savings to buy a house?",
        "What is the valuation limit for using CPF to buy an HDB flat?"
    ]
    
    print("\n" + "="*50)
    print("Testing Vector Database Retrieval")
    print("="*50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[Query {i}]: {query}")
        
        try:
            results = retriever.search(query, top_k=2)
            
            if not results:
                print("  => No results found.")
            else:
                for j, result in enumerate(results, 1):
                    # Our dataset_builder chunker created dicts with 'content' and 'metadata'
                    # The retriever expects 'text' and 'source'. We need to handle this mapping.
                    text = result.get('text') or result.get('content', '')
                    
                    metadata = result.get('metadata', {})
                    source = result.get('source') or metadata.get('source', 'Unknown')
                    
                    dist = result.get('distance', 0.0)
                    
                    print(f"\n  [Result {j}] (Distance: {dist:.4f} | Source: {source})")
                    # Print first 200 characters of the content
                    preview = text[:200].replace('\n', ' ') + "..."
                    print(f"  Content: {preview}")
                    
        except Exception as e:
            print(f"  => Error during search: {e}")

if __name__ == "__main__":
    test_retrieval()