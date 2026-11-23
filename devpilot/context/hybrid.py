"""Adaptive Hybrid Retriever fusing BM25, Dense semantic, Graph expansion, and Adaptive-K."""

from typing import Any

from devpilot.context.adaptive_k import AdaptiveKSelector, TaskComplexityEstimator
from devpilot.context.bm25 import BM25Retriever
from devpilot.context.chunker import CodeChunk
from devpilot.context.dense import DenseSemanticRetriever
from devpilot.context.fusion import min_max_normalize, reciprocal_rank_fusion
from devpilot.context.retriever import RetrievalCandidate, RetrievalTrace, Retriever
from devpilot.repo.graph import RepoDependencyGraph


class AdaptiveHybridRetriever(Retriever):
    """Production research retriever implementing multi-modal RRF and Adaptive-K."""

    def __init__(
        self,
        chunks: list[CodeChunk],
        graph: RepoDependencyGraph | None = None,
        bm25_weight: float = 0.45,
        dense_weight: float = 0.40,
        graph_weight: float = 0.15,
        min_k: int = 2,
        max_k: int = 15,
    ) -> None:
        self.chunks = chunks
        self.graph = graph
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
        self.graph_weight = graph_weight
        self.min_k = min_k
        self.max_k = max_k

        self.bm25 = BM25Retriever(chunks) if chunks else None
        self.dense = DenseSemanticRetriever(chunks) if chunks else None

        # Map file paths to chunk indices
        self.file_to_chunk_indices: dict[str, list[int]] = {}
        for idx, chunk in enumerate(chunks):
            self.file_to_chunk_indices.setdefault(chunk.file_path, []).append(idx)

    async def retrieve(
        self,
        query: str,
        budget_tokens: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[CodeChunk], RetrievalTrace]:
        if not self.chunks or not self.bm25 or not self.dense:
            trace = RetrievalTrace(
                query=query,
                total_candidates=0,
                chosen_k=0,
                cutoff_reason="empty_index",
                complexity_score=1.0,
                total_tokens_retrieved=0,
                candidates=[],
                ranked_files=[],
            )
            return [], trace

        # 1. BM25 Lexical scoring and score calibration
        bm25_raw = self.bm25.score(query)
        bm25_calibrated = min_max_normalize(bm25_raw)
        bm25_ranked = sorted(bm25_calibrated.items(), key=lambda x: x[1], reverse=True)
        bm25_rank_map = {c_idx: r for r, (c_idx, _) in enumerate(bm25_ranked, start=1)}

        # 2. Dense Semantic scoring and score calibration
        dense_raw = self.dense.score(query)
        dense_calibrated = min_max_normalize(dense_raw)
        dense_ranked = sorted(dense_calibrated.items(), key=lambda x: x[1], reverse=True)
        dense_rank_map = {c_idx: r for r, (c_idx, _) in enumerate(dense_ranked, start=1)}

        # 3. Graph expansion scoring with 0.5 decay
        graph_ranked_indices: list[int] = []
        graph_score_map: dict[int, float] = {}
        if self.graph:
            # Seed from top 3 lexical and top 3 semantic chunks
            seed_files = list(
                {self.chunks[c_idx].file_path for c_idx, _ in (bm25_ranked[:3] + dense_ranked[:3])}
            )
            # Expand neighbors up to 1 hop (callers, callees, imports)
            expanded_files = self.graph.expand_neighbors(seed_files, max_hops=1, max_expansion=5)
            for f in expanded_files:
                for c_idx in self.file_to_chunk_indices.get(f, []):
                    if c_idx not in graph_score_map:
                        graph_ranked_indices.append(c_idx)
                        # Decayed score of 0.5 applied to graph-expanded items
                        graph_score_map[c_idx] = 0.5

        graph_rank_map = {c_idx: r for r, c_idx in enumerate(graph_ranked_indices, start=1)}

        # 4. Multi-signal Reciprocal Rank Fusion (RRF)
        ranked_lists = {
            "bm25": [c_idx for c_idx, _ in bm25_ranked],
            "dense": [c_idx for c_idx, _ in dense_ranked],
        }
        weights = {"bm25": self.bm25_weight, "dense": self.dense_weight}

        if graph_ranked_indices:
            ranked_lists["graph"] = graph_ranked_indices
            weights["graph"] = self.graph_weight

        fused = reciprocal_rank_fusion(ranked_lists, weights=weights, k_rrf=60)

        # 5. Task complexity estimation: multiplier in [0.5, 2.0]
        complexity_mult = TaskComplexityEstimator.estimate(query)

        # 6. Adaptive-K selection (Kneedle elbow detection + complexity + budget packer)
        ranked_chunk_pairs = [(self.chunks[c_idx], score) for c_idx, score in fused]
        selected_chunks, chosen_k, cutoff_reason = AdaptiveKSelector.select(
            ranked_chunk_pairs,
            complexity_multiplier=complexity_mult,
            k_min=self.min_k,
            k_max=self.max_k,
            token_budget=budget_tokens,
        )

        selected_set = {c.chunk_id for c in selected_chunks}

        # 7. Deduplicated per-file ranking for Precision@K and Recall@K ground-truth evaluation
        ranked_files: list[str] = []
        seen_files: set[str] = set()
        for c_idx, _ in fused:
            fpath = self.chunks[c_idx].file_path
            if fpath not in seen_files:
                seen_files.add(fpath)
                ranked_files.append(fpath)

        # 8. Rich retrieval trace
        candidate_records: list[RetrievalCandidate] = []
        for c_idx, fused_score in fused[: max(25, self.max_k * 2)]:
            chunk = self.chunks[c_idx]
            candidate_records.append(
                RetrievalCandidate(
                    chunk=chunk,
                    bm25_score=round(bm25_calibrated.get(c_idx, 0.0), 4),
                    bm25_rank=bm25_rank_map.get(c_idx),
                    dense_score=round(dense_calibrated.get(c_idx, 0.0), 4),
                    dense_rank=dense_rank_map.get(c_idx),
                    graph_score=graph_score_map.get(c_idx, 0.0),
                    graph_rank=graph_rank_map.get(c_idx),
                    fused_score=round(fused_score, 6),
                    selected=(chunk.chunk_id in selected_set),
                )
            )

        total_tokens = sum(c.token_count for c in selected_chunks)
        trace = RetrievalTrace(
            query=query,
            total_candidates=len(self.chunks),
            chosen_k=chosen_k,
            cutoff_reason=cutoff_reason,
            complexity_score=complexity_mult,
            total_tokens_retrieved=total_tokens,
            candidates=candidate_records,
            ranked_files=ranked_files,
            metadata={
                "bm25_weight": self.bm25_weight,
                "dense_weight": self.dense_weight,
                "graph_weight": self.graph_weight,
            },
        )

        return selected_chunks, trace
