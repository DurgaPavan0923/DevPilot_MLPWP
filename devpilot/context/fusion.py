"""Reciprocal Rank Fusion (RRF) and score calibration for multi-modal code search."""


def min_max_normalize(scores: list[tuple[int, float]]) -> dict[int, float]:
    """Calibrates raw scores into [0.0, 1.0] interval via min-max normalization."""
    if not scores:
        return {}
    vals = [s for _, s in scores]
    min_v = min(vals)
    max_v = max(vals)
    span = max_v - min_v
    if span <= 1e-9:
        return {idx: 1.0 for idx, _ in scores}
    return {idx: round((s - min_v) / span, 6) for idx, s in scores}


def reciprocal_rank_fusion(
    ranked_lists: dict[str, list[int]],
    weights: dict[str, float] | None = None,
    k_rrf: int = 60,
) -> list[tuple[int, float]]:
    """Fuses multiple ranked candidate index lists using weighted Reciprocal Rank Fusion.

    Formula: RRF_score(d) = sum_{m in M} ( w_m / (k_rrf + r_m(d)) )
    where r_m(d) is 1-based rank position of candidate d in modal ranking m.
    """
    scores: dict[int, float] = {}
    default_weights = weights or dict.fromkeys(ranked_lists.keys(), 1.0)

    for name, r_list in ranked_lists.items():
        w = default_weights.get(name, 1.0)
        for rank_idx, doc_id in enumerate(r_list, start=1):
            contrib = w / (k_rrf + rank_idx)
            scores[doc_id] = scores.get(doc_id, 0.0) + contrib

    fused_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return fused_results
