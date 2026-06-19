import os
import glob
import logging
import yaml
from bs4 import BeautifulSoup
import fitz  # PyMuPDF

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_text_from_html(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(['script', 'style', 'nav', 'footer', 'header']):
            script_or_style.decompose()
            
        text = soup.get_text(separator='\n')
        
        # Clean up empty lines
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
    except Exception as e:
        logging.error(f"Failed to read PDF {pdf_path}: {e}")
    return text

def run_extractor(raw_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    raw_files = glob.glob(os.path.join(raw_dir, "*.*"))
    # Filter out metadata files
    data_files = [f for f in raw_files if not f.endswith('.meta.yaml')]
    
    for file_path in data_files:
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        
        logging.info(f"Extracting text from {filename}...")
        
        if ext.lower() == '.html':
            text = extract_text_from_html(file_path)
        elif ext.lower() == '.pdf':
            text = extract_text_from_pdf(file_path)
        else:
            logging.warning(f"Unsupported file format: {ext}")
            continue
            
        out_path = os.path.join(output_dir, f"{name}.txt")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(text)
            
        # The chunker will now read metadata directly from the raw_data folder
        # We no longer need to copy it to the extracted_text folder

if __name__ == "__main__":
    run_extractor("raw_data", "extracted_text")