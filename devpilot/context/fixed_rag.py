"""Baseline 2: Fixed top-K RAG retriever."""

from typing import Any

from devpilot.context.bm25 import BM25Retriever
from devpilot.context.chunker import CodeChunk
from devpilot.context.retriever import RetrievalCandidate, RetrievalTrace, Retriever


class FixedTopKRetriever(Retriever):
    """Retrieves a static top-K candidates without adaptive elbow cutoff or graph expansion."""

    def __init__(self, chunks: list[CodeChunk], k: int = 5) -> None:
        self.chunks = chunks
        self.k = k
        self.bm25 = BM25Retriever(chunks) if chunks else None

    async def retrieve(
        self,
        query: str,
        budget_tokens: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[CodeChunk], RetrievalTrace]:
        if not self.chunks or not self.bm25:
            trace = RetrievalTrace(
                query=query,
                total_candidates=0,
                chosen_k=0,
                cutoff_reason="empty_index",
                complexity_score=0.0,
                total_tokens_retrieved=0,
                candidates=[],
            )
            return [], trace

        ranked = self.bm25.score(query)
        ranked[: self.k]

        selected_chunks: list[CodeChunk] = []
        candidates: list[RetrievalCandidate] = []
        total_tokens = 0

        for r_idx, (c_idx, score) in enumerate(ranked[: max(self.k * 2, 10)], start=1):
            chunk = self.chunks[c_idx]
            is_selected = r_idx <= self.k
            if is_selected:
                selected_chunks.append(chunk)
                total_tokens += chunk.token_count
            candidates.append(
                RetrievalCandidate(
                    chunk=chunk,
                    bm25_score=round(score, 4),
                    bm25_rank=r_idx,
                    fused_score=round(score, 4),
                    selected=is_selected,
                )
            )

        trace = RetrievalTrace(
            query=query,
            total_candidates=len(self.chunks),
            chosen_k=len(selected_chunks),
            cutoff_reason="fixed_k_limit",
            complexity_score=0.0,
            total_tokens_retrieved=total_tokens,
            candidates=candidates,
        )
        return selected_chunks, trace
