from __future__ import annotations

from sentence_transformers import SentenceTransformer


def load_embedding_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def embed_texts(model: SentenceTransformer, texts: list[str], normalize_embeddings: bool = True):
    return model.encode(texts, normalize_embeddings=normalize_embeddings, show_progress_bar=True)


def embed_query(model: SentenceTransformer, query: str, normalize_embeddings: bool = True) -> list[float]:
    query = (query or "").strip()
    if not query:
        raise ValueError("A pergunta da consulta vetorial não pode ser vazia.")
    vector = model.encode(query, normalize_embeddings=normalize_embeddings)
    return vector.tolist()

