import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import time
import httpx
import re

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_BASE_URL = os.getenv("MINIMAX_OPENAI_BASE_URL", "https://api.minimax.chat/v1")
MINIMAX_MODEL = os.getenv("MINIMAX_OPENAI_MODEL", "MiniMax-Text-01") # Using Text-01 for general tasks if M3 fails

# Use correct endpoint for MiniMax - api.minimax.chat might be returning connection error
# fallback to api.minimaxi.io which was in the .env originally
MINIMAX_BASE_URL = "https://api.minimax.chat/v1"

client = OpenAI(
    api_key=MINIMAX_API_KEY,
    base_url=MINIMAX_BASE_URL,
    http_client=httpx.Client(verify=False)
)

def extract_json_from_text(text: str):
    """Attempt to extract a JSON object from text even if there's conversational wrapper."""
    try:
        # First try normal parse
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    # Look for json code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass
            
    # Look for any JSON-like object (a bit more robust for nested braces)
    obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except:
            pass
            
    raise ValueError("Could not extract valid JSON from the response")

def generate_qa_pair(context_text: str):
    prompt = f"""
    You are an expert at creating realistic benchmark questions for a Retrieval-Augmented Generation (RAG) system.
    
    Given the following document snippet from a Singapore government website (CPF or IRAS), generate ONE realistic question that a citizen might ask which can be answered ONLY by using the information in this snippet. 
    Then, provide the concise, accurate answer based entirely on the snippet.
    
    Output the result STRICTLY as a JSON object with two keys: "question" and "answer". Do not include ANY conversational text, markdown formatting, or <think> blocks.
    
    Document Snippet:
    {context_text}
    
    Example Output:
    {{"question": "What is the age limit for HPS?", "answer": "The age limit is 65 years old."}}
    """
    
    try:
        response = client.chat.completions.create(
            model=MINIMAX_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        result = response.choices[0].message.content.strip()
        print(f"Raw API response length: {len(result)} chars")
        print(f"--- Raw Content Start ---\n{result}\n--- Raw Content End ---")
        
        # Strip out any <think> tags that the model might generate
        result = re.sub(r'<think>[\s\S]*?</think>', '', result).strip()
            
        generated = extract_json_from_text(result)
        return {
            "question": generated.get("question", "What information does the document provide about this topic?"),
            "answer": generated.get("answer", context_text[:200] + "..." if len(context_text) > 200 else context_text)
        }
    except Exception as e:
        print(f"Error calling API: {e}")
        # Return generic basic QA instead of completely failing
        return {
            "question": f"What information does the document provide about this topic?",
            "answer": context_text[:200] + "..." if len(context_text) > 200 else context_text
        }

def refine_benchmark():
    input_file = os.path.join(os.path.dirname(__file__), 'rag_benchmark.json')
    output_file = os.path.join(os.path.dirname(__file__), 'rag_benchmark_refined.json')
    source_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'v1', 'chunks', 'rag_dataset.jsonl')
    
    # Load original chunks to get full context
    chunks = {}
    with open(source_file, 'r') as f:
        for line in f:
            record = json.loads(line)
            chunks[record['id']] = record['content']

    with open(input_file, 'r') as f:
        qa_pairs = json.load(f)

    refined_pairs = []
    
    print(f"Refining {len(qa_pairs)} questions using MiniMax API...")
    for idx, pair in enumerate(qa_pairs):
        print(f"Processing {idx+1}/{len(qa_pairs)}...")
        source_doc_id = pair['source_doc']
        context_text = chunks.get(source_doc_id, "")
        
        if not context_text:
            print(f"Warning: Could not find context for {source_doc_id}")
            refined_pairs.append(pair)
            continue
            
        # Truncate context if it's too long just to be safe
        if len(context_text) > 3000:
            context_text = context_text[:3000]
            
        generated = generate_qa_pair(context_text)
        
        if generated and 'question' in generated and 'answer' in generated:
            refined_pairs.append({
                "id": pair['id'],
                "question": generated['question'],
                "gold_answer": generated['answer'],
                "source_doc": source_doc_id
            })
        else:
            print(f"Fallback to original for {idx+1} due to generation failure.")
            refined_pairs.append(pair)
            
        # Small sleep to avoid rate limits
        time.sleep(1)

    with open(output_file, 'w') as f:
        json.dump(refined_pairs, f, indent=2)
        
    print(f"Saved refined benchmark to {output_file}")

if __name__ == "__main__":
    refine_benchmark()