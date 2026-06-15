# RAG System Design

This document details the implementation of the Retrieval-Augmented Generation (RAG) system for the `agent-eval-lab` project (Week 4).

## 1. Embeddings Strategy

*   **Provider**: OpenAI (Standard industry baseline, easily interchangeable with Voyage AI / Anthropic if needed).
*   **Model**: `text-embedding-3-small`
*   **Vector Dimension**: `1536`
*   **Batching**: Implemented `get_embeddings_batch()` to process multiple text chunks in a single API call, reducing latency and network overhead.

## 2. Document Processing and Chunking

*   **Strategy**: Fixed-size character chunking with overlap.
*   **Chunk Size**: `1000` characters. This size was chosen to provide sufficient context for the LLM without exhausting its context window too quickly when retrieving multiple documents.
*   **Overlap**: `100` characters. This prevents critical context or sentences from being abruptly cut in half across two chunks.
*   **Metadata**: We retain the `source` filename and `chunk_index` alongside the text to give the agent context on *where* the information is coming from.

## 3. Vector Storage (FAISS)

*   **Index Type**: `IndexFlatL2`
*   **Why `IndexFlatL2`?**: It calculates the exact Euclidean distance between the query vector and all document vectors. Since our knowledge base is currently small (a few design docs and notes), exact search is computationally cheap and provides 100% recall accuracy. If the knowledge base grows to millions of documents, we can easily swap this out for `IndexIVFFlat` or HNSW for approximate nearest neighbor search.
*   **Persistence**: The FAISS index is saved to `data/faiss.index` and the associated chunk metadata is saved to `data/metadata.json`.

## 4. Agent Integration

*   **Pattern**: Tool Calling (`search_knowledge_base`)
*   **Implementation**: Rather than proactively fetching context for every user prompt, the RAG system is exposed as a tool to the planner/agent. This allows the agent to decide *when* it needs to look up past bugs, architectural decisions, or documentation. It receives the relevant text chunks directly in its tool execution loop.