# Technical Reference

> For project overview, prerequisites, quick start, and client configuration see [README.md](../README.md).

---

## Components

### 1. Ingestion Pipeline (`Makefile`)

Your host machine manages the initial git synchronization. Keeping repositories outside the Docker image means the image stays lightweight and fast to rebuild — code lives in a shared bind volume, not inside immutable image layers.

```makefile
.PHONY: clone-repos build run

clone-repos:
	@echo "Cloning repositories..."
	python3 src/cloner.py

build:
	docker compose build

run: clone-repos build
	docker compose up
```

---

### 2. RAG Indexer (`src/indexer.py`)

**ChromaDB** runs embedded within the application process — no separate database container required. It persists state to the `vector_db/` bind mount so embeddings survive container restarts.

**Chunking strategy:**

- **By file extension:** Only source files are indexed (`.py`, `.go`, `.java`, `.cpp`, `.js`, `.ts`). Binary files, images, and lockfiles (`package-lock.json`, `go.sum`) are excluded.
- **Current implementation:** Each file is stored as a single document, keyed by its relative path. Metadata includes `source` (relative path), `filename`, and `repo` (top-level directory name). Function/class-level chunking is a planned improvement that would increase retrieval precision for large files.

```python
import os

import chromadb
from chromadb.utils import embedding_functions

REPOS_DIR = "/app/repositories"
VECTOR_DB_DIR = "/app/vector_db"
COLLECTION_NAME = "repo_codebase"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

SOURCE_EXTENSIONS = {".py", ".go", ".java", ".cpp", ".js", ".ts"}


def initialize_rag() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=VECTOR_DB_DIR)

    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=emb_fn,
    )

    if not os.path.exists(REPOS_DIR):
        print(f"[indexer] repositories dir not found at {REPOS_DIR}, skipping indexing.")
        return collection

    indexed = 0
    for root, _, files in os.walk(REPOS_DIR):
        for filename in files:
            if os.path.splitext(filename)[1] not in SOURCE_EXTENSIONS:
                continue

            file_path = os.path.join(root, filename)
            try:
                with open(file_path, "r", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue

            if not content.strip():
                continue

            rel_path = os.path.relpath(file_path, REPOS_DIR)
            repo_name = rel_path.split(os.sep)[0]

            collection.upsert(
                documents=[content],
                metadatas=[{
                    "source": rel_path,
                    "filename": filename,
                    "repo": repo_name,
                }],
                ids=[rel_path],
            )
            indexed += 1

    print(f"[indexer] Indexed {indexed} files into ChromaDB.")
    return collection
```

---

### 3. MCP Server (`src/server.py`)

Uses the official Anthropic `mcp` Python SDK via `FastMCP`. When hosted in Docker, the client communicates with the server over standard input/output streams (`stdio`).

**Exposed tools:**

- `search_codebase(query, n_results)` — semantic search over all indexed source files
- `list_available_repositories()` — lists the repositories currently mounted and available

```python
import os

from mcp.server.fastmcp import FastMCP

from indexer import initialize_rag

mcp = FastMCP("Mock Interview RAG Server")

collection = initialize_rag()


@mcp.tool()
def search_codebase(query: str, n_results: int = 3) -> str:
    """
    Searches the cloned repositories for relevant code context,
    architectural patterns, or language implementations matching the query.
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    formatted = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        formatted.append(f"--- File: {meta['source']} ---\n{doc}\n")

    return "\n".join(formatted) if formatted else "No results found."


@mcp.tool()
def list_available_repositories() -> list[str]:
    """Returns a list of repositories currently loaded in the RAG context."""
    try:
        return os.listdir("/app/repositories")
    except FileNotFoundError:
        return []


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

---

### 4. Container Configuration

#### `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["python", "src/server.py"]
```

#### `docker-compose.yml`

```yaml
services:
  mcp-server:
    build: .
    volumes:
      - ./repositories:/app/repositories
      - ./vector_db:/app/vector_db
    stdin_open: true
    tty: true
```

#### `requirements.txt`

```
mcp
chromadb
sentence-transformers
```

---

## Interview Flow

Once connected, the interaction works as follows:

1. **User** tells the LLM client: _"I want to do a mock interview based on the repositories available."_
2. **LLM client** calls `list_available_repositories` via the MCP server to discover what codebases are loaded.
3. **LLM client** prompts the user: _"Great, I see we have a few systems here. Let's start with your Go backend authentication logic."_
4. **LLM client** silently calls `search_codebase(query="JWT authentication middleware")` to retrieve the relevant code chunks.
5. **LLM client** formulates a tailored interview question using the retrieved snippet as direct context.
