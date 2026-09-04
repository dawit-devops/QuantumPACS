"""RAG engine — FAISS-backed semantic search over the vector store.

Pipeline
--------
1.  Load the persisted FAISS index + chunk metadata via ``load_index``.
2.  ``retrieve`` embeds a query with the same Sentence-Transformers model,
    searches the index, and returns ranked ``Chunk`` results.
3.  ``generate`` optionally calls an LLM (OpenAI or local) to synthesise an
    answer grounded in the retrieved chunks.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from rag.config import RAGConfig, get_config
from rag.indexer import load_index
from rag.models import Chunk, Query

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global singletons (lazy-init)
# ---------------------------------------------------------------------------
_model: SentenceTransformer | None = None
_index: faiss.Index | None = None
_chunks: list[Chunk] = []


def _get_model() -> SentenceTransformer:
    """Return the shared embedding model (created once)."""
    global _model
    if _model is None:
        cfg = get_config()
        log.info("Loading embedding model %s …", cfg.model_name)
        _model = SentenceTransformer(cfg.model_name)
    return _model


def _ensure_index() -> tuple[faiss.Index, list[Chunk]]:
    """Load the FAISS index + chunks if not already loaded."""
    global _index, _chunks
    if _index is None:
        cfg = get_config()
        _index, _chunks = load_index(cfg.index_path, cfg.chunks_path)
        log.info("Loaded FAISS index with %d vectors.", _index.ntotal)
    assert _index is not None
    return _index, _chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def retrieve(
    query: str,
    top_k: int = 5,
    doc_id: str | None = None,
    *,
    config: RAGConfig | None = None,
) -> list[Chunk]:
    """Semantic search over the vector store.

    Parameters
    ----------
    query:
        Free-text user query.
    top_k:
        Maximum chunks to return.
    doc_id:
        If given, restrict results to chunks from this document.
    config:
        Optional override for the RAG configuration.

    Returns
    -------
    list[Chunk]
        Ranked list of matching chunks with scores.
    """
    cfg = config or get_config()
    model = _get_model()
    index, chunks = _ensure_index()

    # Embed query
    q_vec: np.ndarray = model.encode([query], normalize_embeddings=True)
    q_vec = q_vec.astype("float32")

    # Search — fetch extra candidates if we need to filter by doc_id
    fetch_k = top_k * 5 if doc_id else top_k
    distances, indices = index.search(q_vec, min(fetch_k, index.ntotal))

    results: list[Chunk] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0:
            continue
        chunk = chunks[idx]
        if doc_id and chunk.doc_id != doc_id:
            continue
        chunk_with_score = Chunk(
            doc_id=chunk.doc_id,
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            heading=chunk.heading,
            chunk_index=chunk.chunk_index,
            score=float(dist),
        )
        results.append(chunk_with_score)
        if len(results) >= top_k:
            break

    return results


def generate(
    query: str,
    chunks: list[Chunk] | None = None,
    *,
    config: RAGConfig | None = None,
) -> dict[str, Any]:
    """Generate an answer grounded in retrieved chunks.

    Parameters
    ----------
    query:
        User question.
    chunks:
        Pre-retrieved chunks.  If *None*, ``retrieve`` is called first.
    config:
        Optional override.

    Returns
    -------
    dict
        ``{"answer": str, "sources": list[dict]}``
    """
    cfg = config or get_config()

    if chunks is None:
        chunks = retrieve(query, top_k=cfg.top_k, config=cfg)

    # Format context for the LLM
    context_parts: list[str] = []
    for i, c in enumerate(chunks, 1):
        header = f"[{i}] {c.heading or 'Untitled'} (doc={c.doc_id}, chunk={c.chunk_id})"
        context_parts.append(f"{header}\n{c.text}")
    context = "\n\n---\n\n".join(context_parts)

    # If no LLM backend is configured, return the raw context
    if not cfg.llm_backend:
        return {
            "answer": (
                "LLM backend not configured.  Here are the most relevant "
                "chunks for your query:\n\n" + context
            ),
            "sources": [_chunk_to_source(c) for c in chunks],
        }

    # LLM generation (simplified — real impl would call OpenAI / local model)
    prompt = (
        f"Answer the following question using ONLY the provided context.\n\n"
        f"## Context\n\n{context}\n\n"
        f"## Question\n\n{query}\n\n"
        f"## Answer\n"
    )

    answer = _call_llm(prompt, cfg)
    return {
        "answer": answer,
        "sources": [_chunk_to_source(c) for c in chunks],
    }


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _chunk_to_source(chunk: Chunk) -> dict[str, Any]:
    return {
        "doc_id": chunk.doc_id,
        "chunk_id": chunk.chunk_id,
        "heading": chunk.heading,
        "score": chunk.score,
    }


def _call_llm(prompt: str, cfg: RAGConfig) -> str:  # pragma: no cover
    """Call the configured LLM backend.  Returns the response text."""
    if cfg.llm_backend == "openai":
        import openai

        client = openai.OpenAI(api_key=cfg.openai_api_key)
        model = cfg.openai_model or "gpt-4o-mini"
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2048,
        )
        return resp.choices[0].message.content or ""

    if cfg.llm_backend == "local":
        # Placeholder for local model integration (llama.cpp, Ollama, etc.)
        return "[local model not yet implemented — raw context returned]"

    raise ValueError(f"Unknown llm_backend: {cfg.llm_backend!r}")


def reset() -> None:
    """Reset global singletons (useful in tests)."""
    global _model, _index, _chunks
    _model = None
    _index = None
    _chunks = []
