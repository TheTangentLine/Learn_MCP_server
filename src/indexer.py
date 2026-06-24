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
