"""Evaluation metrics for retrieval and task completion benchmarks."""

from typing import Any

from pydantic import BaseModel, Field


class RetrievalMetrics(BaseModel):
    precision_at_k: float = Field(..., ge=0.0, le=1.0)
    recall_at_k: float = Field(..., ge=0.0, le=1.0)
    k: int = Field(..., ge=1)
    retrieved_count: int = Field(..., ge=0)
    gold_count: int = Field(..., ge=0)


class BenchmarkMetrics(BaseModel):
    task_count: int = 0
    completion_rate: float = 0.0
    test_pass_rate: float = 0.0
    avg_precision_at_k: float = 0.0
    avg_recall_at_k: float = 0.0
    recovery_success_rate: float = 0.0
    avg_steps: float = 0.0
    avg_tokens: float = 0.0
    avg_cost_usd: float = 0.0
    avg_duration_sec: float = 0.0


def compute_retrieval_metrics(
    retrieved_files: list[str],
    gold_files: list[str],
    k: int = 5,
) -> RetrievalMetrics:
    """Computes Precision@K and Recall@K against gold modified files from benchmark patches."""
    if not gold_files:
        return RetrievalMetrics(
            precision_at_k=1.0 if not retrieved_files else 0.0,
            recall_at_k=1.0,
            k=k,
            retrieved_count=len(retrieved_files),
            gold_count=0,
        )

    # Normalize file paths
    norm_gold = {f.replace("\\", "/").strip("/") for f in gold_files}
    top_k_retrieved = [f.replace("\\", "/").strip("/") for f in retrieved_files[:k]]
    retrieved_set = set(top_k_retrieved)

    # Compute intersection
    hits = len(retrieved_set & norm_gold)

    precision = hits / float(k) if k > 0 else 0.0
    recall = hits / float(len(norm_gold)) if len(norm_gold) > 0 else 0.0

    return RetrievalMetrics(
        precision_at_k=round(precision, 4),
        recall_at_k=round(recall, 4),
        k=k,
        retrieved_count=len(top_k_retrieved),
        gold_count=len(norm_gold),
    )


def compute_task_metrics(results: list[dict[str, Any]]) -> BenchmarkMetrics:
    """Computes aggregated benchmark performance metrics across a run."""
    n = len(results)
    if n == 0:
        return BenchmarkMetrics()

    completed = sum(1 for r in results if r.get("status") == "COMPLETED")
    tests_passed = sum(1 for r in results if r.get("tests_passed", False))
    total_steps = sum(r.get("steps", 0) for r in results)
    total_tokens = sum(r.get("total_tokens", 0) for r in results)
    total_cost = sum(r.get("total_cost_usd", 0.0) for r in results)
    total_duration = sum(r.get("duration_sec", 0.0) for r in results)

    precisions = [r.get("precision_at_k", 0.0) for r in results if "precision_at_k" in r]
    recalls = [r.get("recall_at_k", 0.0) for r in results if "recall_at_k" in r]

    # Recovery success: errors that were successfully resolved
    total_recoveries = sum(r.get("recoveries_count", 0) for r in results)
    successful_recoveries = sum(
        r.get("recoveries_count", 0) for r in results if r.get("status") == "COMPLETED"
    )
    rec_rate = (successful_recoveries / total_recoveries) if total_recoveries > 0 else 1.0

    return BenchmarkMetrics(
        task_count=n,
        completion_rate=round(completed / n, 4),
        test_pass_rate=round(tests_passed / n, 4),
        avg_precision_at_k=round(sum(precisions) / len(precisions), 4) if precisions else 0.0,
        avg_recall_at_k=round(sum(recalls) / len(recalls), 4) if recalls else 0.0,
        recovery_success_rate=round(rec_rate, 4),
        avg_steps=round(total_steps / n, 2),
        avg_tokens=round(total_tokens / n, 2),
        avg_cost_usd=round(total_cost / n, 4),
        avg_duration_sec=round(total_duration / n, 2),
    )
