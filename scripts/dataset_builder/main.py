import os
import logging
from scraper import run_scraper
from extractor import run_extractor
from chunker import run_chunker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    config_path = os.path.join(base_dir, "sources.yaml")
    raw_dir = os.path.join(base_dir, "raw_data")
    extracted_dir = os.path.join(base_dir, "extracted_text")
    output_dir = os.path.join(base_dir, "output")
    
    logging.info("=== Phase 1: Downloading Documents ===")
    run_scraper(config_path, raw_dir)
    
    logging.info("=== Phase 2: Extracting Text ===")
    run_extractor(raw_dir, extracted_dir)
    
    logging.info("=== Phase 3: Chunking & Formatting ===")
    run_chunker(extracted_dir, output_dir)
    
    logging.info("=== Pipeline Complete! ===")
    logging.info(f"RAG dataset is available at: {os.path.join(output_dir, 'rag_dataset.jsonl')}")

if __name__ == "__main__":
    main()