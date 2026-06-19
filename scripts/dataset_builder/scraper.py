import os
import time
import requests
import yaml
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_sources(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f).get('sources', [])

def download_file(url, output_path):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(response.content)
        logging.info(f"Successfully downloaded: {url} to {output_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to download {url}: {e}")
        return False

def run_scraper(config_path, output_dir):
    sources = load_sources(config_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for source in sources:
        name = source['name']
        url = source['url']
        file_type = source['type']
        
        # Determine extension based on type
        ext = '.pdf' if file_type.lower() == 'pdf' else '.html'
        output_path = os.path.join(output_dir, f"{name}{ext}")
        
        logging.info(f"Downloading {name}...")
        success = download_file(url, output_path)
        
        if success:
            # Save metadata alongside the raw file
            meta_path = os.path.join(output_dir, f"{name}.meta.yaml")
            with open(meta_path, 'w') as f:
                yaml.dump(source, f)
        
        # Be polite to servers
        time.sleep(1)

if __name__ == "__main__":
    run_scraper("sources.yaml", "raw_data")