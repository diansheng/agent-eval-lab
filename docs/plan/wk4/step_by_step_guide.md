# Week 4: Add RAG (Retrieval-Augmented Generation) - Step-by-Step Guide

This guide provides a highly detailed, prescriptive breakdown for implementing the Week 4 objectives. 

*(Note: Since the MiniMax embedding documentation is currently deprecated/unavailable, this guide has been updated to use OpenAI's native embeddings or Anthropic's recommended partner, Voyage AI. Both are industry standards.)*

## 📚 Phase 1: Reading & Research (2-3h)

### Step 1.1: Embeddings API Documentation (Choose One)

**Option A: OpenAI (Recommended for ease of use)**
*   **Link:** [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
*   **Action Items:**
    1.  Look at the `text-embedding-3-small` model (this is the current standard).
    2.  Note the **exact vector dimension size**: 1536. This is crucial for FAISS initialization.
    3.  Familiarize yourself with the API payload (`input`, `model`).

**Option B: Anthropic (via Voyage AI)**
*   **Link:** [Anthropic Embeddings Overview](https://docs.anthropic.com/en/docs/build-with-claude/embeddings)
*   **Action Items:**
    1.  Read how Anthropic handles embeddings (they don't have native embeddings, they officially partner with Voyage AI).
    2.  Check the Voyage AI docs for models like `voyage-3` or `voyage-code-2` (great for codebases).
    3.  Note the dimension size for the model you choose (e.g., `voyage-3` is 1024 dimensions).

### Step 1.2: FAISS (Facebook AI Similarity Search) Basics
*   **Link:** [FAISS GitHub Repository & Getting Started Wiki](https://github.com/facebookresearch/faiss/wiki/Getting-Started)
*   **Action Items:**
    1.  Read the "Getting Started" guide.
    2.  Understand how `faiss.IndexFlatL2(dimension)` works (it measures L2/Euclidean distance between vectors).
    3.  Look at the basic syntax for adding vectors (`index.add(vectors)`) and searching (`index.search(query_vector, k)`).

---

## 🛠️ Phase 2: Build & Implementation (5-6h)

### Step 2.1: Environment Setup
1.  Navigate to your repository root: `cd agent-eval-lab`
2.  Activate your virtual environment: `source .venv/bin/activate` (or your equivalent).
3.  Install FAISS, numpy, and the OpenAI SDK (if using Option A):
    ```bash
    pip install faiss-cpu numpy openai
    ```

### Step 2.2: Prepare the Knowledge Base
1.  Create a directory for the knowledge base: 
    ```bash
    mkdir -p docs/knowledge_base
    ```
2.  Copy your existing markdown files into this folder:
    *   `week1_notes.md`
    *   `wk2/architecture_v1.md`
    *   `workflow_design.md`
    *   *(Optional)* Create a dummy file named `auth_implementation.md` with some fake code to test the retrieval later.

### Step 2.3: Document Loading and Chunking
1.  Create a new file: `app/rag/document_processor.py`
2.  **Write `load_documents(directory_path)`**:
    *   Use Python's `os` or `pathlib` to iterate through all `.md` files in `docs/knowledge_base`.
    *   Read and return the text content along with the filename.
3.  **Write `chunk_text(text, chunk_size=1000, overlap=100)`**:
    *   Write a loop that splits the text into smaller strings (chunks) so they fit in the embedding context window.
    *   Return a list of dictionaries containing metadata: 
        `[{"text": "chunk content...", "source": "architecture_v1.md", "chunk_index": 0}, ...]`

### Step 2.4: The Embedding Client
1.  Create file: `app/rag/embedder.py`
2.  **Write `get_embedding(text: str) -> list[float]`**:
    *   Initialize the `OpenAI` client.
    *   Pass the chunk text to the embeddings endpoint: `client.embeddings.create(input=[text], model="text-embedding-3-small")`.
    *   Extract and return the vector: `response.data[0].embedding`.
3.  **Write `get_embeddings_batch(texts: list[str]) -> list[list[float]]`**:
    *   Modify the above function to accept a list of strings and return a list of vectors to save API calls.

### Step 2.5: Build the Vector Store (FAISS)
1.  Create file: `app/rag/vector_store.py`
2.  **Create a class `VectorStore`**:
    *   **`__init__(self, dimension: int)`**: Initialize `self.index = faiss.IndexFlatL2(dimension)` and an empty list `self.metadata = []`. (Pass `1536` if using `text-embedding-3-small`).
    *   **`add_documents(self, chunks: list[dict], embeddings: list[list[float]])`**:
        *   Convert the `embeddings` list to a `float32` numpy array: `np.array(embeddings, dtype=np.float32)`.
        *   Call `self.index.add(numpy_array)`.
        *   Append the `chunks` to `self.metadata`. *(FAISS index 0 will correspond to `self.metadata[0]`)*.
    *   **`save(self, index_path, meta_path)`**: Use `faiss.write_index(self.index, index_path)` and save `self.metadata` using the `json` module.

### Step 2.6: The Retrieval Layer
1.  Create file: `app/rag/retriever.py`
2.  **Write `search(query: str, top_k: int = 3) -> list[dict]`**:
    *   Get the embedding for the user's `query` using your `get_embedding()` function.
    *   Convert the embedding to a float32 numpy array of shape `(1, dimension)`.
    *   Search FAISS: `distances, indices = vector_store.index.search(query_vector, top_k)`.
    *   Loop through the returned `indices[0]` and map them back to your `self.metadata` to retrieve the original text chunks.
    *   Return the matching text chunks and their source file names.

### Step 2.7: Agent Integration
1.  Open your agent file (e.g., `app/agent/planner.py` or where you define your tools).
2.  **Create the Tool Schema**: 
    *   Define a new tool named `search_knowledge_base`.
    *   Description: *"Search the project documentation to answer questions about architecture, past bugs, or setup."*
    *   Parameters: `query` (type: string).
3.  **Update Tool Executor**: Ensure your agent's execution loop routes calls for `search_knowledge_base` to the `search()` function you wrote in Step 2.6, and returns the chunk text back to the LLM.

---

## 📝 Phase 3: Deliverables & Testing (1-2h)

### Step 3.1: Manual Testing
1.  Create a quick script `scripts/test_rag.py` to initialize the store, process the docs, and test the search function directly.
2.  Run the query: *"Has this bug happened before?"* (Verify it retrieves related design docs or notes).
3.  Run the query: *"Where is authentication implemented?"* (Verify it retrieves the dummy file you created).

### Step 3.2: Git Commits
Commit your work progressively:
1.  `git add app/rag/embedder.py app/rag/document_processor.py`
    *   `git commit -m "feat: embedding pipeline using OpenAI"`
2.  `git add app/rag/vector_store.py app/rag/retriever.py`
    *   `git commit -m "feat: retrieval layer with FAISS"`
3.  `git add app/agent/`
    *   `git commit -m "feat: rag integration as agent tool"`

### Step 3.3: Write the Design Document
1.  Create `rag_design.md` in the root of your repository.
2.  **Document your implementation decisions**:
    *   Which embedding model you used (e.g., `text-embedding-3-small`) and its vector dimension (1536).
    *   Your exact chunk size and overlap parameters.
    *   Why you chose `IndexFlatL2` in FAISS.
    *   How the agent interacts with the RAG system (as a tool vs. pre-fetched context).