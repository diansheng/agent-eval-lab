import os
import glob
import json
import yaml
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_chunker(extracted_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    text_files = glob.glob(os.path.join(extracted_dir, "*.txt"))
    
    # Configure the text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    
    all_chunks = []
    
    for txt_path in text_files:
        name = os.path.splitext(os.path.basename(txt_path))[0]
        logging.info(f"Chunking {name}...")
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        # Load metadata directly from raw_data directory
        meta_path = os.path.join(os.path.dirname(extracted_dir), "raw_data", f"{name}.meta.yaml")
        metadata = {}
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                metadata = yaml.safe_load(f)
                
        # Split text
        chunks = text_splitter.split_text(text)
        
        for i, chunk in enumerate(chunks):
            doc = {
                "id": f"{name}_{i}",
                "content": chunk,
                "metadata": {
                    "source": metadata.get("source", "Unknown"),
                    "url": metadata.get("url", ""),
                    "title": metadata.get("name", name),
                    "chunk_index": i
                }
            }
            all_chunks.append(doc)
            
    # Save to JSONL format
    out_file = os.path.join(output_dir, "rag_dataset.jsonl")
    with open(out_file, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk) + '\n')
            
    logging.info(f"Saved {len(all_chunks)} chunks to {out_file}")

if __name__ == "__main__":
    run_chunker("extracted_text", "output")