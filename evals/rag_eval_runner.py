import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv
import httpx
import faiss
import numpy as np

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_BASE_URL = os.getenv("MINIMAX_OPENAI_BASE_URL", "https://api.minimaxi.io/v1")
MINIMAX_MODEL = os.getenv("MINIMAX_OPENAI_MODEL", "MiniMax-Text-01")

client = OpenAI(
    api_key=MINIMAX_API_KEY,
    base_url=MINIMAX_BASE_URL,
    http_client=httpx.Client(verify=False)
)

# Load FAISS index and metadata
index_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'v1', 'vector_store', 'index.faiss')
metadata_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'v1', 'vector_store', 'metadata.json')

index = None
metadata = []

if os.path.exists(index_path) and os.path.exists(metadata_path):
    index = faiss.read_index(index_path)
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

def get_embedding(text: str) -> list[float]:
    """Get embedding from MiniMax API."""
    try:
        response = client.embeddings.create(
            model="embo-01",
            input=[text]
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0.0] * 1536  # Default fallback size

def query_rag_pipeline(question: str, top_k: int = 3):
    """
    Real RAG pipeline using FAISS and MiniMax API.
    Returns the generated answer and the list of retrieved source document IDs.
    """
    if index is None or not metadata:
        print("Warning: FAISS index or metadata not found. Returning mock response.")
        return {
            "answer": "FAISS index not available. This is a mock answer.",
            "retrieved_docs": ["mock_doc_1"]
        }
        
    # 1. Embed the question
    query_vector = np.array([get_embedding(question)], dtype=np.float32)
    
    # 2. Search FAISS index
    distances, indices = index.search(query_vector, top_k)
    
    retrieved_docs = []
    contexts = []
    
    for idx in indices[0]:
        if idx != -1 and idx < len(metadata):
            doc = metadata[idx]
            # Handle different metadata structures based on how it was built
            doc_id = doc.get("id", doc.get("source", f"unknown_{idx}"))
            if "chunk_index" in doc and "source" in doc:
                doc_id = f"{doc['source']}_{doc['chunk_index']}"
                
            retrieved_docs.append(doc_id)
            
            content = doc.get("content", doc.get("text", ""))
            contexts.append(f"Document ID: {doc_id}\nContent: {content}")
            
    # 3. Generate Answer using LLM
    context_str = "\n\n".join(contexts)
    prompt = f"""
    Answer the following question based ONLY on the provided context documents.
    If you cannot answer the question based on the context, say "I don't know".
    Always cite the Document ID in your answer.
    
    Question: {question}
    
    Context:
    {context_str}
    """
    
    try:
        response = client.chat.completions.create(
            model=MINIMAX_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating answer: {e}")
        answer = "Error generating answer from LLM."
        
    return {
        "answer": answer,
        "retrieved_docs": retrieved_docs
    }

def score_retrieval_recall(expected_source: str, retrieved_docs: list[str]) -> int:
    """
    Checks if the expected source document was retrieved in the top-k results.
    Returns 1 if found, 0 otherwise.
    """
    return 1 if expected_source in retrieved_docs else 0

def score_citation_quality(expected_source: str, answer: str) -> int:
    """
    Checks if the final answer explicitly cites the expected source document.
    Returns 1 if cited, 0 otherwise.
    """
    return 1 if expected_source in answer else 0

def score_answer_accuracy(expected_answer: str, actual_answer: str) -> int:
    """
    LLM-as-a-judge metric to compare the generated answer against the gold answer.
    In a real scenario, you'd call the MiniMax API with a prompt asking it to grade 
    the answer on a pass/fail (1/0) basis.
    """
    prompt = f"""
    You are an expert evaluator. Compare the ACTUAL ANSWER to the EXPECTED ANSWER.
    If the ACTUAL ANSWER contains the same core information and is factually correct based on the EXPECTED ANSWER, output '1'.
    If it is incorrect, contradicts, or is missing core information, output '0'.
    
    EXPECTED ANSWER: {expected_answer}
    ACTUAL ANSWER: {actual_answer}
    
    You must ONLY output the number 1 or 0. Do not output anything else.
    """
    
    try:
        response = client.chat.completions.create(
            model=MINIMAX_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10
        )
        result = response.choices[0].message.content.strip()
        
        # Clean up any potential markdown or <think> blocks
        import re
        result = re.sub(r'<think>[\s\S]*?</think>', '', result).strip()
        
        if '1' in result and '0' not in result:
            return 1
        elif '0' in result and '1' not in result:
            return 0
        else:
            # Fallback parsing
            return 1 if result == '1' else 0
            
    except Exception as e:
        print(f"Error calling LLM-as-a-judge: {e}")
        return 0

def run_evaluation(benchmark_file: str):
    print(f"Loading benchmark from {benchmark_file}...")
    with open(benchmark_file, "r") as f:
        qa_pairs = json.load(f)

    results = []
    total_recall = 0
    total_accuracy = 0
    total_citation = 0

    for idx, item in enumerate(qa_pairs):
        question = item["question"]
        gold_answer = item["gold_answer"]
        expected_source = item["source_doc"]

        print(f"Running Eval {idx+1}/{len(qa_pairs)}: {question}")
        
        # 1. Run the RAG pipeline
        response = query_rag_pipeline(question)
        actual_answer = response["answer"]
        retrieved_docs = response["retrieved_docs"]

        # 2. Score the results
        recall_score = score_retrieval_recall(expected_source, retrieved_docs)
        accuracy_score = score_answer_accuracy(gold_answer, actual_answer)
        citation_score = score_citation_quality(expected_source, actual_answer)

        total_recall += recall_score
        total_accuracy += accuracy_score
        total_citation += citation_score

        results.append({
            "id": item["id"],
            "question": question,
            "recall": recall_score,
            "accuracy": accuracy_score,
            "citation": citation_score
        })

    # 3. Calculate and print final metrics
    num_questions = len(qa_pairs)
    print("\n--- Final RAG Evaluation Report ---")
    print(f"Total Questions: {num_questions}")
    print(f"Retrieval Recall: {(total_recall / num_questions) * 100:.2f}%")
    print(f"Answer Accuracy: {(total_accuracy / num_questions) * 100:.2f}%")
    print(f"Citation Quality: {(total_citation / num_questions) * 100:.2f}%")

    # Save results to file
    report_path = os.path.join(os.path.dirname(benchmark_file), "rag_eval_results.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Detailed results saved to {report_path}")

if __name__ == "__main__":
    benchmark_path = os.path.join(os.path.dirname(__file__), "rag_benchmark.json")
    if not os.path.exists(benchmark_path):
        print(f"Benchmark file not found at {benchmark_path}")
        sys.exit(1)
    
    run_evaluation(benchmark_path)