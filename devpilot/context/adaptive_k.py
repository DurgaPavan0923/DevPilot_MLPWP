"""Adaptive-K selection: real Kneedle knee detection, task complexity estimation, and budget packing."""

import re

from devpilot.context.chunker import CodeChunk


class TaskComplexityEstimator:
    """Estimates task difficulty and outputs a budget scaling multiplier in [0.5, 2.0]."""

    IDENTIFIER_REGEX = re.compile(
        r"\b(?:[a-z]+(?:_[a-z0-9]+)+|[a-z]+[A-Z0-9][a-zA-Z0-9]*|[A-Z][a-z0-9]+[A-Z][a-zA-Z0-9]*)\b"
    )
    STACK_TRACE_REGEX = re.compile(
        r'(?:Traceback \(most recent call last\):|File ".*?", line \d+|[A-Za-z]+Error:|[A-Za-z]+Exception:)',
        re.MULTILINE,
    )
    MULTI_FILE_REGEX = re.compile(
        r"\b(?:multi[- ]file|multiple files|across modules|refactor|migration|architecture|subsystem|integration)\b",
        re.IGNORECASE,
    )

    @classmethod
    def estimate(cls, query: str) -> float:
        """Computes calibrated complexity multiplier in [0.5, 2.0].

        Features:
        - Query length (words)
        - Identifier count (snake_case / camelCase)
        - Stack trace / Exception presence
        - Multi-file and refactoring indicators
        """
        multiplier = 1.0

        # 1. Query length
        words = len(query.split())
        if words < 8:
            multiplier -= 0.25
        elif words > 60:
            multiplier += 0.35
        elif words > 25:
            multiplier += 0.15

        # 2. Identifier count
        identifiers = cls.IDENTIFIER_REGEX.findall(query)
        if len(identifiers) >= 6:
            multiplier += 0.30
        elif len(identifiers) >= 3:
            multiplier += 0.15

        # 3. Stack trace / Exception detector
        if cls.STACK_TRACE_REGEX.search(query):
            multiplier += 0.40

        # 4. Multi-file hint detector
        if cls.MULTI_FILE_REGEX.search(query):
            multiplier += 0.30

        return max(0.5, min(2.0, round(multiplier, 2)))


class AdaptiveKSelector:
    """Detects score curve knee/elbow using Kneedle and packs chunks within token budget."""

    @staticmethod
    def detect_knee(scores: list[float], sensitivity: float = 1.0) -> int:
        """Finds elbow/knee index on a descending score curve using the Kneedle algorithm.

        Returns 1-based cutoff index K.
        """
        n = len(scores)
        if n <= 2:
            return n

        max_s = scores[0]
        min_s = scores[-1]
        range_s = max_s - min_s
        if range_s <= 1e-9:
            return min(3, n)

        # Normalized coordinates: x in [0, 1], y in [0, 1]
        # For a descending convex score curve, the knee is where
        # the curve drops below the diagonal connecting (0, 1) and (1, 0)
        # or where difference d_i = (1 - x_i) - y_i is maximized.
        max_dist = -1.0
        knee_idx = 2

        for idx, score in enumerate(scores):
            x = idx / (n - 1)
            y = (score - min_s) / range_s
            # Distance from diagonal connecting (0, 1) and (1, 0)
            dist = (1.0 - x) - y
            if dist > max_dist:
                max_dist = dist
                knee_idx = idx + 1

        return max(2, min(n, knee_idx))

    @classmethod
    def select(
        cls,
        ranked_chunks: list[tuple[CodeChunk, float]],
        complexity_multiplier: float = 1.0,
        k_min: int = 2,
        k_max: int = 15,
        relevance_threshold_ratio: float = 0.20,
        token_budget: int | None = None,
    ) -> tuple[list[CodeChunk], int, str]:
        """Dynamically selects top-K chunks using elbow detection, complexity scaling,

        and token budget constraints.
        """
        if not ranked_chunks:
            return [], 0, "no_candidates"

        scores = [item[1] for item in ranked_chunks]
        max_score = scores[0]

        # 1. Elbow detection via Kneedle
        knee_k = cls.detect_knee(scores)

        # 2. Scale by complexity multiplier: clamp in [k_min, k_max]
        scaled_k = int(round(knee_k * complexity_multiplier))
        chosen_k = max(k_min, min(k_max, min(scaled_k, len(ranked_chunks))))
        cutoff_reason = "knee_and_complexity"

        # 3. Relevance floor filter: drop chunks below threshold unless list would be empty
        relevance_floor = max_score * relevance_threshold_ratio
        candidates_to_pack: list[CodeChunk] = []

        for chunk, score in ranked_chunks[:chosen_k]:
            if score < relevance_floor and len(candidates_to_pack) >= k_min:
                cutoff_reason = "relevance_threshold_cutoff"
                break
            candidates_to_pack.append(chunk)

        if not candidates_to_pack and ranked_chunks:
            candidates_to_pack.append(ranked_chunks[0][0])

        # 4. Atomic symbol token budget packing
        if token_budget is not None and token_budget > 0:
            packed_chunks: list[CodeChunk] = []
            used_tokens = 0
            for chunk in candidates_to_pack:
                if used_tokens + chunk.token_count > token_budget and packed_chunks:
                    cutoff_reason = "token_budget_exhausted"
                    break
                packed_chunks.append(chunk)
                used_tokens += chunk.token_count
            return packed_chunks, len(packed_chunks), cutoff_reason

        return candidates_to_pack, len(candidates_to_pack), cutoff_reason
