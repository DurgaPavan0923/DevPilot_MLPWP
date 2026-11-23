"""Lexical BM25 code retriever implementation."""

import math
import re
from collections import Counter, defaultdict

from devpilot.context.chunker import CodeChunk


def tokenize_code(text: str) -> list[str]:
    """Tokenizes code text splitting on camelCase, snake_case, and non-alphanumeric chars."""
    # Split camelCase
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
    tokens = re.findall(r"[A-Za-z0-9_]{2,}", s2)
    return [t.lower() for t in tokens if len(t) > 1]


class BM25Retriever:
    """Okapi BM25 implementation optimized for source code retrieval."""

    def __init__(self, chunks: list[CodeChunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.doc_count = len(chunks)
        self.doc_lengths: list[int] = []
        self.doc_freqs: dict[str, int] = defaultdict(int)
        self.term_freqs: list[Counter[str]] = []

        self._build_index()

    def _build_index(self) -> None:
        total_len = 0
        for chunk in self.chunks:
            tokens = tokenize_code(chunk.content + " " + chunk.file_path)
            length = len(tokens)
            self.doc_lengths.append(length)
            total_len += length

            tf = Counter(tokens)
            self.term_freqs.append(tf)
            for term in tf:
                self.doc_freqs[term] += 1

        self.avg_doc_len = total_len / max(1, self.doc_count)

    def _compute_idf(self, term: str) -> float:
        df = self.doc_freqs.get(term, 0)
        return math.log(((self.doc_count - df + 0.5) / (df + 0.5)) + 1.0)

    def score(self, query: str) -> list[tuple[int, float]]:
        """Returns sorted list of (chunk_index, bm25_score) tuples."""
        query_terms = tokenize_code(query)
        if not query_terms or self.doc_count == 0:
            return [(i, 0.0) for i in range(self.doc_count)]

        scores: list[float] = [0.0] * self.doc_count

        for term in query_terms:
            if term not in self.doc_freqs:
                continue
            idf = self._compute_idf(term)
            for idx, tf in enumerate(self.term_freqs):
                freq = tf.get(term, 0)
                if freq == 0:
                    continue
                doc_len = self.doc_lengths[idx]
                numerator = freq * (self.k1 + 1.0)
                denominator = freq + self.k1 * (
                    1.0 - self.b + self.b * (doc_len / max(1e-5, self.avg_doc_len))
                )
                scores[idx] += idf * (numerator / denominator)

        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        return indexed_scores
