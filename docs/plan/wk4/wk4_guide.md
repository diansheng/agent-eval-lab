# Week 4: Add RAG - Step-by-Step Guide

## Overview
This week focuses on giving your agent a Knowledge Base using Retrieval-Augmented Generation (RAG). You will use MiniMax Embeddings and FAISS to allow the agent to answer questions based on project documentation.

## Step 1: Reading & Research
- **Task**: Read the MiniMax Embeddings and Retrieval documentation.
- **Focus**: Understand how to call the embeddings API and the expected input/output formats for vector generation.

## Step 2: Setup Environment
- **Task**: Install necessary libraries for local vector storage.
- **Action**: Run `pip install faiss-cpu numpy` (and any text chunking library you prefer, such as `tiktoken` or `langchain-text-splitters`).

## Step 3: Prepare the Knowledge Base
- **Task**: Gather documents to embed.
- **Action**: Collect markdown docs, project docs, and design docs into a specific folder (e.g., `docs/`).
- **Action**: Write a text chunker script to split these documents into manageable pieces (e.g., 500-1000 tokens per chunk). Keep track of metadata (source file, chunk index).

## Step 4: Build the Embedding Pipeline
- **Task**: Convert text chunks into vector embeddings.
- **Action**: Write a script that iterates over your text chunks, calls the MiniMax Embeddings API, and retrieves the vector representations.
- **Action**: Initialize a FAISS index and add these vectors to it. Save the index locally (e.g., `faiss_index.bin`) along with a mapping of vector IDs to the original text and metadata (e.g., in a `metadata.json` file).

## Step 5: Implement the Retrieval Layer
- **Task**: Create a search function to retrieve context.
- **Action**: Write a function `search_docs(query: str, top_k: int = 3)` that:
  1. Embeds the user `query` using the MiniMax API.
  2. Searches the FAISS index for the `top_k` nearest vectors.
  3. Retrieves and returns the corresponding text chunks from your metadata mapping.

## Step 6: Agent Integration
- **Task**: Give the agent access to the retrieval layer.
- **Action**: Wrap `search_docs` as a callable tool (e.g., `Retrieval Tool`) that the agent can use, similar to the GitHub tools from Week 2.
- **Action**: Update the agent's system prompt to instruct it to use the `Retrieval Tool` when asked questions about project history, design, or documentation.

## Step 7: Testing
- **Task**: Verify the RAG pipeline works end-to-end.
- **Action**: Ask the agent test questions like:
  - *"Has this bug happened before?"*
  - *"Where is authentication implemented?"*
- **Action**: Check the tracing/logs to ensure the agent successfully calls the tool, receives the correct text chunks, and formulates an accurate answer based on the retrieved context.

## Step 8: Final Deliverables
- **Commits**:
  - `feat: add embedding pipeline and faiss index generation`
  - `feat: implement retrieval layer`
  - `feat: integrate rag tool into agent workflow`
- **Documentation**: Write `rag_design.md` detailing your chunking strategy, embedding model usage, and how the agent interacts with the retrieved context.
