import os
import requests
from dotenv import load_dotenv

load_dotenv()

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_API_URL = "https://api.minimax.chat/v1/embeddings"

def get_embedding(text: str, model: str = "embo-01") -> list[float]:
    """
    Retrieves the embedding vector for a single string using MiniMax Native API.
    """
    text = text.replace("\n", " ")
    
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "texts": [text],
        "type": "db"
    }
    
    response = requests.post(MINIMAX_API_URL, headers=headers, json=data)
    response.raise_for_status()
    
    result = response.json()
    if "vectors" not in result or not result["vectors"]:
        raise ValueError(f"Failed to get embedding from MiniMax: {result}")
        
    return result["vectors"][0]

def get_embeddings_batch(texts: list[str], model: str = "embo-01") -> list[list[float]]:
    """
    Retrieves embedding vectors for a list of strings in a single API call using MiniMax.
    """
    texts = [t.replace("\n", " ") for t in texts]
    
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "texts": texts,
        "type": "db"
    }
    
    response = requests.post(MINIMAX_API_URL, headers=headers, json=data)
    response.raise_for_status()
    
    result = response.json()
    if "vectors" not in result or not result["vectors"]:
        raise ValueError(f"Failed to get batch embeddings from MiniMax: {result}")
        
    return result["vectors"]
