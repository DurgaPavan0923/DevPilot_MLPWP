"""Context retrieval subsystem: symbol chunking, hybrid retrieval, RRF fusion, and Adaptive-K."""

from devpilot.context.adaptive_k import AdaptiveKSelector, TaskComplexityEstimator
from devpilot.context.chunker import CodeChunk, SymbolChunker
from devpilot.context.fixed_rag import FixedTopKRetriever
from devpilot.context.hybrid import AdaptiveHybridRetriever
from devpilot.context.no_retrieval import NoRetrieval
from devpilot.context.retriever import RetrievalCandidate, RetrievalTrace, Retriever

__all__ = [
    "CodeChunk",
    "SymbolChunker",
    "Retriever",
    "RetrievalCandidate",
    "RetrievalTrace",
    "NoRetrieval",
    "FixedTopKRetriever",
    "AdaptiveHybridRetriever",
    "AdaptiveKSelector",
    "TaskComplexityEstimator",
]
