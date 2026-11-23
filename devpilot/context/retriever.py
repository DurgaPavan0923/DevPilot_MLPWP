"""Abstract retriever interface and audit trace schemas."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from devpilot.context.chunker import CodeChunk


class RetrievalCandidate(BaseModel):
    chunk: CodeChunk
    bm25_score: float = 0.0
    bm25_rank: int | None = None
    dense_score: float = 0.0
    dense_rank: int | None = None
    graph_score: float = 0.0
    graph_rank: int | None = None
    fused_score: float = 0.0
    selected: bool = False


class RetrievalTrace(BaseModel):
    query: str
    total_candidates: int
    chosen_k: int
    cutoff_reason: str
    complexity_score: float
    total_tokens_retrieved: int
    candidates: list[RetrievalCandidate] = Field(default_factory=list)
    ranked_files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Retriever(ABC):
    """Abstract interface across all context retrieval strategies."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        budget_tokens: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[CodeChunk], RetrievalTrace]:
        """Retrieves most relevant code chunks alongside full audit trace."""
        pass
