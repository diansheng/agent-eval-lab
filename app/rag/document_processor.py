import os
import glob

def load_documents(directory_path: str) -> list[dict]:
    """
    Loads all markdown files from the specified directory.
    Returns a list of dicts with 'filename' and 'content'.
    """
    documents = []
    search_pattern = os.path.join(directory_path, "**/*.md")
    
    for filepath in glob.glob(search_pattern, recursive=True):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            documents.append({
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "content": content
            })
            
    return documents

def chunk_text(text: str, source: str, chunk_size: int = 1000, overlap: int = 100) -> list[dict]:
    """
    Splits text into chunks of `chunk_size` characters with `overlap` characters.
    """
    chunks = []
    start = 0
    text_length = len(text)
    chunk_index = 0
    
    while start < text_length:
        end = start + chunk_size
        chunk_content = text[start:end]
        chunks.append({
            "text": chunk_content,
            "source": source,
            "chunk_index": chunk_index
        })
        start += chunk_size - overlap
        chunk_index += 1
        
    return chunks

def process_directory(directory_path: str, chunk_size: int = 1000, overlap: int = 100) -> list[dict]:
    """
    Loads all documents from a directory and chunks them.
    """
    documents = load_documents(directory_path)
    all_chunks = []
    
    for doc in documents:
        doc_chunks = chunk_text(
            text=doc["content"], 
            source=doc["filename"], 
            chunk_size=chunk_size, 
            overlap=overlap
        )
        all_chunks.extend(doc_chunks)
        
    return all_chunks
