"""Dense semantic code retriever with sentence-transformers, caching, and TF-IDF fallback."""

import hashlib
import json
import math
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from devpilot.context.bm25 import tokenize_code
from devpilot.context.chunker import CodeChunk
from devpilot.core.logging import get_logger

logger = get_logger("devpilot.context.dense")

# Attempt importing sentence_transformers
try:
    from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False


def _compute_chunk_hash(chunk: CodeChunk) -> str:
    """Computes deterministic SHA-256 hash of code chunk content and identity."""
    raw = f"{chunk.file_path}:{chunk.symbol_name or ''}:{chunk.start_line}:{chunk.end_line}:{chunk.content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """Calculates cosine similarity between two dense float vectors."""
    if len(vec1) != len(vec2) or not vec1:
        return 0.0
    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0
    for a, b in zip(vec1, vec2, strict=True):
        dot += a * b
        norm1 += a * a
        norm2 += b * b
    if norm1 <= 1e-12 or norm2 <= 1e-12:
        return 0.0
    return dot / (math.sqrt(norm1) * math.sqrt(norm2))


class DenseSemanticRetriever:
    """Semantic vector retriever using sentence-transformers (all-MiniLM-L6-v2) or TF-IDF fallback.

    Features:
    - On-disk hash cache to avoid recomputing unchanged chunks across sessions.
    - Incremental updates for modified or added chunks.
    - Graceful deterministic fallback to TF-IDF with explicit logging if dependencies are missing.
    """

    def __init__(
        self,
        chunks: list[CodeChunk],
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: Path | None = None,
    ) -> None:
        self.chunks = chunks
        self.model_name = model_name
        self.cache_dir = cache_dir or Path(".devpilot/cache")
        self.cache_file = self.cache_dir / "embeddings_cache.json"

        self.is_neural = _HAS_SENTENCE_TRANSFORMERS
        self.model: Any = None
        self.chunk_embeddings: list[list[float]] = []

        # TF-IDF fallback structures
        self.doc_vectors: list[dict[str, float]] = []
        self.doc_magnitudes: list[float] = []

        self._embedding_cache: dict[str, list[float]] = {}
        self._load_cache()

        if self.is_neural:
            try:
                logger.info("loading_sentence_transformer_model", model=self.model_name)
                self.model = SentenceTransformer(self.model_name)
                self._build_dense_embeddings()
            except Exception as exc:
                logger.warning(
                    "sentence_transformers_init_failed_falling_back_to_tfidf",
                    error=str(exc),
                )
                self.is_neural = False
                self._build_tfidf_vectors()
        else:
            logger.warning("sentence_transformers unavailable; falling back to TF-IDF retriever")
            self._build_tfidf_vectors()

    def _load_cache(self) -> None:
        """Loads cached embeddings from disk if present."""
        if self.cache_file.exists():
            try:
                self._embedding_cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception:
                self._embedding_cache = {}

    def _persist_cache(self) -> None:
        """Persists memory embedding cache to disk."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(self._embedding_cache), encoding="utf-8")
        except Exception:
            pass

    def _build_dense_embeddings(self) -> None:
        """Builds or fetches cached embeddings for all chunks."""
        self.chunk_embeddings = []
        chunks_to_encode: list[tuple[int, str, str]] = []  # (index, hash, text)

        for idx, chunk in enumerate(self.chunks):
            ch_hash = _compute_chunk_hash(chunk)
            if ch_hash in self._embedding_cache:
                self.chunk_embeddings.append(self._embedding_cache[ch_hash])
            else:
                self.chunk_embeddings.append([])
                doc_text = f"{chunk.file_path} {chunk.symbol_name or ''}\n{chunk.content}"
                chunks_to_encode.append((idx, ch_hash, doc_text))

        if chunks_to_encode and self.model is not None:
            texts = [item[2] for item in chunks_to_encode]
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            for (idx, ch_hash, _), emb in zip(chunks_to_encode, embeddings, strict=True):
                emb_list = [float(v) for v in emb]
                self.chunk_embeddings[idx] = emb_list
                self._embedding_cache[ch_hash] = emb_list
            self._persist_cache()

    def _build_tfidf_vectors(self) -> None:
        """Builds term-frequency vectors for TF-IDF fallback."""
        self.doc_vectors = []
        self.doc_magnitudes = []
        for chunk in self.chunks:
            tokens = tokenize_code(f"{chunk.content} {chunk.symbol_name or ''} {chunk.file_path}")
            counts = Counter(tokens)
            vec: dict[str, float] = {}
            for t, count in counts.items():
                vec[t] = 1.0 + math.log(count)
            mag = math.sqrt(sum(v * v for v in vec.values()))
            self.doc_vectors.append(vec)
            self.doc_magnitudes.append(max(1e-9, mag))

    def update_chunks(self, new_chunks: list[CodeChunk]) -> None:
        """Incrementally re-indexes only new or changed chunks."""
        self.chunks = new_chunks
        if self.is_neural:
            self._build_dense_embeddings()
        else:
            self._build_tfidf_vectors()

    def score(self, query: str) -> list[tuple[int, float]]:
        """Computes semantic similarity scores between query and all chunks."""
        if not self.chunks:
            return []

        if self.is_neural and self.model is not None:
            q_emb = [float(v) for v in self.model.encode([query])[0]]
            results: list[tuple[int, float]] = []
            for idx, c_emb in enumerate(self.chunk_embeddings):
                sim = _cosine_similarity(q_emb, c_emb)
                # Normalize cosine in [-1, 1] to [0, 1]
                calibrated_sim = max(0.0, min(1.0, (sim + 1.0) / 2.0))
                results.append((idx, round(calibrated_sim, 6)))
            results.sort(key=lambda x: x[1], reverse=True)
            return results

        # TF-IDF fallback scoring
        query_tokens = tokenize_code(query)
        if not query_tokens:
            return [(i, 0.0) for i in range(len(self.chunks))]

        q_counts = Counter(query_tokens)
        q_vec = {t: 1.0 + math.log(c) for t, c in q_counts.items()}
        q_mag = math.sqrt(sum(v * v for v in q_vec.values()))
        if q_mag <= 0:
            return [(i, 0.0) for i in range(len(self.chunks))]

        tfidf_results: list[tuple[int, float]] = []
        for idx, d_vec in enumerate(self.doc_vectors):
            dot_product = 0.0
            for term, q_val in q_vec.items():
                if term in d_vec:
                    dot_product += q_val * d_vec[term]
            sim = dot_product / (q_mag * self.doc_magnitudes[idx])
            tfidf_results.append((idx, max(0.0, min(1.0, round(sim, 6)))))

        tfidf_results.sort(key=lambda x: x[1], reverse=True)
        return tfidf_results
