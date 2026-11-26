import logging
import math
import re
from collections import Counter

import faiss
import numpy as np

from app.config import settings
from app.ingestion import (
    _index_lock,
    _load_index,
    _load_metadata,
    generate_embedding,
)

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "their",
    "this", "to", "was", "were", "what", "when", "where", "which",
    "who", "why", "with", "would", "does", "did", "do", "has", "have",
    "had", "can", "could", "should", "will", "your", "my", "about",
}


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+(?:[._'-][a-zA-Z0-9]+)*", text.lower())
    return [token for token in tokens if token not in STOP_WORDS]


def _bm25_scores(query_tokens: list[str], documents: list[dict]) -> list[float]:
    if not query_tokens or not documents:
        return [0.0] * len(documents)

    tokenized_docs = [_tokenize(item.get("text", "")) for item in documents]
    doc_lengths = [len(tokens) for tokens in tokenized_docs]
    average_length = sum(doc_lengths) / max(len(doc_lengths), 1)

    document_frequency = Counter()
    for tokens in tokenized_docs:
        document_frequency.update(set(tokens))

    total_docs = len(tokenized_docs)
    k1 = 1.5
    b = 0.75
    scores = []

    query_frequency = Counter(query_tokens)

    for tokens, doc_length in zip(tokenized_docs, doc_lengths):
        frequencies = Counter(tokens)
        score = 0.0

        for term, qf in query_frequency.items():
            frequency = frequencies.get(term, 0)
            if frequency == 0:
                continue

            df = document_frequency.get(term, 0)
            inverse_document_frequency = math.log(
                1 + (total_docs - df + 0.5) / (df + 0.5)
            )

            denominator = frequency + k1 * (
                1 - b + b * doc_length / max(average_length, 1)
            )
            term_score = inverse_document_frequency * (
                frequency * (k1 + 1) / denominator
            )

            score += term_score * (1 + math.log(qf))

        scores.append(score)

    return scores


def retrieve_documents(
    query: str,
    top_k: int | None = None,
    document_ids: list[str] | None = None,
) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    limit = top_k if top_k is not None else settings.RETRIEVAL_TOP_K
    if limit <= 0:
        raise ValueError("top_k must be positive.")

    query_tokens = _tokenize(query)
    query_vector = np.asarray(
        [generate_embedding(query)],
        dtype=np.float32,
    )

    with _index_lock:
        index = _load_index()
        metadata = _load_metadata()

        if index.ntotal == 0 or not metadata:
            return []

        candidates = []
        for chunk_id, item in metadata.items():
            if document_ids and item.get("document_id") not in document_ids:
                continue

            candidates.append({
                "chunk_id": str(chunk_id),
                "document_id": item.get("document_id"),
                "filename": item.get("filename"),
                "chunk_index": item.get("chunk_index"),
                "text": item.get("text", ""),
            })

        if not candidates:
            return []

        bm25_values = _bm25_scores(query_tokens, candidates)
        bm25_order = sorted(
            range(len(candidates)),
            key=lambda position: bm25_values[position],
            reverse=True,
        )

        bm25_rank = {}
        for rank, position in enumerate(bm25_order, start=1):
            if bm25_values[position] > 0:
                bm25_rank[candidates[position]["chunk_id"]] = rank

        vector_rank = {}
        vector_score = {}

        search_count = min(index.ntotal, max(limit * 10, 50))
        distances, identifiers = index.search(query_vector, search_count)

        for rank, (score, identifier) in enumerate(
            zip(distances[0], identifiers[0]),
            start=1,
        ):
            if identifier < 0:
                continue

            chunk_id = str(int(identifier))
            if chunk_id not in {item["chunk_id"] for item in candidates}:
                continue

            vector_rank[chunk_id] = rank
            vector_score[chunk_id] = float(score)

        candidate_by_id = {
            item["chunk_id"]: item
            for item in candidates
        }

        all_ids = set(bm25_rank) | set(vector_rank)
        if not all_ids:
            return []

        # Reciprocal Rank Fusion combines lexical BM25 and FAISS rankings.
        rrf_constant = 60
        fused = []

        for chunk_id in all_ids:
            bm25_position = bm25_rank.get(chunk_id)
            vector_position = vector_rank.get(chunk_id)

            fused_score = 0.0
            if bm25_position is not None:
                fused_score += 1.0 / (rrf_constant + bm25_position)
            if vector_position is not None:
                fused_score += 1.0 / (rrf_constant + vector_position)

            fused.append((
                fused_score,
                chunk_id,
                bm25_position,
                vector_position,
            ))

        fused.sort(key=lambda item: item[0], reverse=True)
        maximum_score = fused[0][0] if fused else 1.0

        results = []
        for fused_score, chunk_id, bm25_position, vector_position in fused[:limit]:
            item = candidate_by_id[chunk_id]
            results.append({
                **item,
                "score": round(fused_score / maximum_score, 4),
                "relevance_score": round(fused_score / maximum_score, 4),
                "vector_score": round(vector_score.get(chunk_id, 0.0), 4),
                "bm25_rank": bm25_position,
                "vector_rank": vector_position,
            })

    logger.info(
        "Hybrid retrieval returned %d chunks for query with %d terms",
        len(results),
        len(query_tokens),
    )
    return results


def prepare_context(results: list[dict]) -> str:
    if not results:
        return (
            "I couldn't find relevant information in the uploaded "
            "documents to answer this question."
        )

    sections = []
    for index, result in enumerate(results, start=1):
        sections.append(
            f"[Source {index}: {result.get('filename', 'Unknown')} | "
            f"Chunk {result.get('chunk_index', 'Unknown')}]\n"
            f"{result.get('text', '')}"
        )

    return "\n\n".join(sections)


def prepare_citations(results: list[dict]) -> list[dict]:
    return [
        {
            "document_id": result.get("document_id"),
            "filename": result.get("filename"),
            "chunk_id": result.get("chunk_id"),
            "chunk_index": result.get("chunk_index"),
            "score": result.get("score"),
            "vector_score": result.get("vector_score"),
            "bm25_rank": result.get("bm25_rank"),
        }
        for result in results
    ]
