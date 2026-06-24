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
