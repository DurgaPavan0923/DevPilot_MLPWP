"""Baseline 1: No retrieval (Basic Agent relying purely on tool calls)."""

from typing import Any

from devpilot.context.chunker import CodeChunk
from devpilot.context.retriever import RetrievalTrace, Retriever


class NoRetrieval(Retriever):
    """Null retriever returning empty context for Basic Agent baseline."""

    async def retrieve(
        self,
        query: str,
        budget_tokens: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[CodeChunk], RetrievalTrace]:
        trace = RetrievalTrace(
            query=query,
            total_candidates=0,
            chosen_k=0,
            cutoff_reason="no_retrieval_baseline",
            complexity_score=0.0,
            total_tokens_retrieved=0,
            candidates=[],
        )
        return [], trace
