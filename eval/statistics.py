"""Statistical significance, exact binomial McNemar test, bootstrap CIs, and Holm correction."""

import math
import random
from typing import NamedTuple


class McNemarResult(NamedTuple):
    statistic: float
    p_value: float
    odds_ratio: float
    is_significant: bool
    test_type: str  # "exact_binomial" or "asymptotic_chisq"
    contingency_table: dict[str, int]


def _exact_binomial_p_value(b: int, c: int) -> float:
    """Computes exact two-sided binomial p-value under H0: p = 0.5 for discordant pairs n = b + c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    # Cumulative binomial distribution: sum_{i=0..k} comb(n, i) * (0.5)^n
    cumulative = 0.0
    for i in range(k + 1):
        cumulative += math.comb(n, i)
    p_val = 2.0 * cumulative * (0.5**n)
    return min(1.0, p_val)


def mcnemar_test(
    outcomes_a: list[bool],
    outcomes_b: list[bool],
    continuity_correction: bool = True,
    exact_threshold: int = 25,
) -> McNemarResult:
    """Performs McNemar's paired test for comparing binary outcomes on identical tasks.

    - If discordant pairs (b + c) < exact_threshold (default 25): uses exact two-sided binomial test.
    - If discordant pairs >= exact_threshold: uses Edwards continuity corrected Chi-squared test.
    """
    if len(outcomes_a) != len(outcomes_b):
        raise ValueError("Outcome vectors must have identical length for paired testing")

    n = len(outcomes_a)
    if n == 0:
        return McNemarResult(
            0.0, 1.0, 1.0, False, "exact_binomial", {"a": 0, "b": 0, "c": 0, "d": 0}
        )

    a = b = c = d = 0
    for res_a, res_b in zip(outcomes_a, outcomes_b, strict=False):
        if res_a and res_b:
            a += 1
        elif res_a and not res_b:
            b += 1
        elif not res_a and res_b:
            c += 1
        else:
            d += 1

    discordant = b + c
    table = {"a": a, "b": b, "c": c, "d": d}

    if discordant == 0:
        return McNemarResult(0.0, 1.0, 1.0, False, "exact_binomial", table)

    odds_ratio = (b / float(c)) if c > 0 else (float("inf") if b > 0 else 1.0)
    capped_or = 999.0 if odds_ratio == float("inf") else round(odds_ratio, 4)

    # When discordant < 25, use exact binomial distribution
    if discordant < exact_threshold:
        p_val = _exact_binomial_p_value(b, c)
        return McNemarResult(
            statistic=float(min(b, c)),
            p_value=round(p_val, 5),
            odds_ratio=capped_or,
            is_significant=(p_val < 0.05),
            test_type="exact_binomial",
            contingency_table=table,
        )

    # Edwards continuity-corrected Chi-squared test
    diff = abs(b - c)
    if continuity_correction:
        stat = ((diff - 1.0) ** 2) / float(discordant) if diff > 0 else 0.0
    else:
        stat = (diff**2) / float(discordant)

    # 1-df chi-square p-value: p = erfc(sqrt(stat / 2))
    p_value = math.erfc(math.sqrt(stat / 2.0))

    return McNemarResult(
        statistic=round(stat, 4),
        p_value=round(p_value, 5),
        odds_ratio=capped_or,
        is_significant=(p_value < 0.05),
        test_type="asymptotic_chisq",
        contingency_table=table,
    )


def bootstrap_confidence_interval(
    data: list[float],
    n_bootstrap: int = 10_000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Computes non-parametric bootstrap confidence interval for the sample mean.

    Returns (sample_mean, ci_lower, ci_upper).
    """
    if not data:
        return 0.0, 0.0, 0.0

    n = len(data)
    rng = random.Random(seed)
    bootstrap_means: list[float] = []

    for _ in range(n_bootstrap):
        sample = [data[rng.randint(0, n - 1)] for _ in range(n)]
        bootstrap_means.append(sum(sample) / float(n))

    bootstrap_means.sort()
    alpha = (1.0 - ci) / 2.0
    lower_idx = int(alpha * n_bootstrap)
    upper_idx = int((1.0 - alpha) * n_bootstrap)

    sample_mean = sum(data) / float(n)
    ci_lower = bootstrap_means[lower_idx]
    ci_upper = bootstrap_means[min(n_bootstrap - 1, upper_idx)]

    return round(sample_mean, 4), round(ci_lower, 4), round(ci_upper, 4)


def holm_bonferroni_correction(p_values: list[float]) -> list[tuple[float, float, bool]]:
    """Applies the Holm-Bonferroni step-down procedure for family-wise error rate control.

    Returns list of tuples: (original_p, adjusted_p, is_significant_at_05).
    """
    m = len(p_values)
    if m == 0:
        return []

    # Sort p-values while preserving original indices
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted_indexed: list[tuple[int, float, float, bool]] = []

    running_max = 0.0
    for rank_idx, (orig_idx, p_val) in enumerate(indexed):
        multiplier = m - rank_idx
        adj_p = min(1.0, p_val * multiplier)
        running_max = max(running_max, adj_p)
        adjusted_indexed.append((orig_idx, p_val, round(running_max, 5), running_max < 0.05))

    # Restore original order
    adjusted_indexed.sort(key=lambda x: x[0])
    return [(p, adj, sig) for _, p, adj, sig in adjusted_indexed]
