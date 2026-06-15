import os
from openai import OpenAI

# Initialize the client. 
# It will automatically pick up OPENAI_API_KEY from the environment.
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

def get_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """
    Retrieves the embedding vector for a single string.
    """
    # Replace newlines as recommended by OpenAI for older models, 
    # though less strictly necessary for v3 models.
    text = text.replace("\n", " ")
    
    response = client.embeddings.create(
        input=[text],
        model=model
    )
    return response.data[0].embedding

def get_embeddings_batch(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """
    Retrieves embedding vectors for a list of strings in a single API call.
    """
    # Clean the texts
    texts = [t.replace("\n", " ") for t in texts]
    
    response = client.embeddings.create(
        input=texts,
        model=model
    )
    
    # Sort the results by index to ensure they match the input order
    sorted_data = sorted(response.data, key=lambda x: x.index)
    return [item.embedding for item in sorted_data]
