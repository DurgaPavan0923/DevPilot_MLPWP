"""DevPilot research evaluation framework."""

from eval.dataset import BenchmarkTask, TaskSuiteLoader
from eval.metrics import BenchmarkMetrics, compute_retrieval_metrics, compute_task_metrics
from eval.runner import ExperimentRunner
from eval.statistics import bootstrap_confidence_interval, mcnemar_test

__all__ = [
    "compute_retrieval_metrics",
    "compute_task_metrics",
    "BenchmarkMetrics",
    "mcnemar_test",
    "bootstrap_confidence_interval",
    "BenchmarkTask",
    "TaskSuiteLoader",
    "ExperimentRunner",
]
