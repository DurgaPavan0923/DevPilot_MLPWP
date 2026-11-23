"""Production experiment runner: isolated execution, real test runs, caching, and parallel evaluation."""

import asyncio
import contextlib
import json
import shutil
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from devpilot.agent.runtime import AgentRuntime
from devpilot.core.logging import get_logger
from devpilot.core.types import AgentConfigPreset
from devpilot.llm.adapters.mock import MockProvider
from devpilot.llm.base import LLMProvider
from devpilot.verify.runner import VerificationRunner
from eval.dataset import BenchmarkTask, TaskSuiteLoader, ensure_eval_repos
from eval.metrics import compute_retrieval_metrics, compute_task_metrics
from eval.statistics import (
    bootstrap_confidence_interval,
    holm_bonferroni_correction,
    mcnemar_test,
)

logger = get_logger("devpilot.eval.runner")


class ExperimentRunner:
    """Executes benchmark evaluations across agent configurations under controlled, isolated conditions."""

    def __init__(
        self,
        workspace_dir: Path,
        results_dir: Path,
        llm: LLMProvider | None = None,
        seeds: list[int] | None = None,
        max_concurrency: int = 4,
        cost_cap_per_task: float = 2.0,
        enable_cache: bool = True,
    ) -> None:
        self.workspace_dir = workspace_dir.resolve()
        self.results_dir = results_dir.resolve()
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.llm = llm or MockProvider(model="mock-eval-model")
        self.seeds = seeds or [42, 137, 2026]
        self.max_concurrency = max_concurrency
        self.cost_cap_per_task = cost_cap_per_task
        self.enable_cache = enable_cache
        self.cache_file = self.results_dir / "eval_results_cache.json"

        self._cache: dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.enable_cache and self.cache_file.exists():
            try:
                self._cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception:
                self._cache = {}

    def _persist_cache(self) -> None:
        if self.enable_cache:
            with contextlib.suppress(Exception):
                self.cache_file.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")

    def _make_cache_key(self, task_id: str, preset: str, seed: int, model: str) -> str:
        return f"{task_id}::{preset}::{seed}::{model}"

    async def run_single_task_trial(
        self,
        task: BenchmarkTask,
        preset: AgentConfigPreset,
        seed: int,
        source_repo_dir: Path,
    ) -> dict[str, Any]:
        """Executes a single benchmark task in an isolated temporary directory with real test verification."""
        model_name = getattr(self.llm, "model", "mock-model")
        cache_key = self._make_cache_key(task.task_id, preset.value, seed, model_name)

        if self.enable_cache and cache_key in self._cache:
            logger.info("eval_task_cache_hit", key=cache_key)
            return self._cache[cache_key]

        start_time = time.monotonic()
        temp_dir = Path(tempfile.mkdtemp(prefix=f"eval_{task.task_id}_{preset.value}_{seed}_"))

        try:
            # Create isolated copy of task repository
            if source_repo_dir.exists():
                shutil.copytree(source_repo_dir, temp_dir, dirs_exist_ok=True)

            session_id = f"eval_{task.task_id}_{preset.value}_s{seed}"
            runtime = AgentRuntime(
                session_id=session_id,
                repo_root=temp_dir,
                llm=self.llm,
                preset=preset,
                max_steps=25,
                max_cost_usd=self.cost_cap_per_task,
            )

            # Execute agent run
            run_result = await runtime.run(task.instruction)

            # Execute real test suite in isolated directory
            verifier = VerificationRunner(temp_dir)
            verify_report = await verifier.run_verification(
                modified_files=list(runtime.fsm.data.modified_files)
            )

            # Determine actual test passing status
            tests_passed = verify_report.passed

            # Precision@K and Recall@K on retrieved files vs gold files
            retrieved_files = list(runtime.fsm.data.modified_files)
            metrics = compute_retrieval_metrics(retrieved_files, task.gold_files, k=5)

            elapsed_sec = round(time.monotonic() - start_time, 2)
            record = {
                "task_id": task.task_id,
                "repo": task.repo,
                "preset": preset.value,
                "seed": seed,
                "model": model_name,
                "status": run_result["status"],
                "tests_passed": tests_passed,
                "verification_status": verify_report.status,
                "test_stdout": verify_report.stdout[:500],
                "steps": run_result["steps"],
                "total_tokens": run_result["total_tokens"],
                "total_cost_usd": run_result["total_cost_usd"],
                "duration_sec": elapsed_sec,
                "recoveries_count": run_result["recoveries_count"],
                "precision_at_k": metrics.precision_at_k,
                "recall_at_k": metrics.recall_at_k,
                "modified_files": run_result["modified_files"],
                "gold_files": task.gold_files,
            }

            if self.enable_cache:
                self._cache[cache_key] = record
                self._persist_cache()

            return record

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def run_comparative_experiment(
        self,
        tasks: list[BenchmarkTask] | None = None,
        presets: list[AgentConfigPreset] | None = None,
    ) -> dict[str, Any]:
        """Runs multi-configuration, multi-seed comparative benchmark with parallel execution and statistics."""
        eval_tasks = tasks or TaskSuiteLoader.load_builtin_tasks()
        eval_presets = presets or [
            AgentConfigPreset.BASIC,
            AgentConfigPreset.FIXED_RAG,
            AgentConfigPreset.FULL,
        ]

        # Ensure task repositories are populated on disk
        task_repos = ensure_eval_repos(self.workspace_dir)

        semaphore = asyncio.Semaphore(self.max_concurrency)
        all_trials: list[dict[str, Any]] = []

        async def _bounded_trial(t: BenchmarkTask, p: AgentConfigPreset, s: int) -> dict[str, Any]:
            async with semaphore:
                repo_path = task_repos.get(t.repo, self.workspace_dir / t.repo)
                return await self.run_single_task_trial(t, p, s, repo_path)

        # Build list of coroutines across tasks, presets, and seeds
        coros = [
            _bounded_trial(task, preset, seed)
            for preset in eval_presets
            for task in eval_tasks
            for seed in self.seeds
        ]

        logger.info(
            "eval_experiment_started",
            total_trials=len(coros),
            presets=[p.value for p in eval_presets],
            tasks=len(eval_tasks),
            seeds=self.seeds,
        )

        all_trials = await asyncio.gather(*coros)

        # Organize trials by preset
        trials_by_preset: dict[str, list[dict[str, Any]]] = {p.value: [] for p in eval_presets}
        for trial in all_trials:
            trials_by_preset[trial["preset"]].append(trial)

        # Compute aggregated metrics per preset
        configs_summary: dict[str, dict[str, Any]] = {}
        for p_name, p_trials in trials_by_preset.items():
            bm = compute_task_metrics(p_trials)
            summary = bm.model_dump()

            # Compute 95% bootstrap confidence intervals for key continuous metrics
            p_precisions = [t["precision_at_k"] for t in p_trials]
            p_recalls = [t["recall_at_k"] for t in p_trials]
            p_steps = [float(t["steps"]) for t in p_trials]
            p_tokens = [float(t["total_tokens"]) for t in p_trials]

            summary["bootstrap_ci"] = {
                "precision_at_k": list(bootstrap_confidence_interval(p_precisions)),
                "recall_at_k": list(bootstrap_confidence_interval(p_recalls)),
                "steps": list(bootstrap_confidence_interval(p_steps)),
                "tokens": list(bootstrap_confidence_interval(p_tokens)),
            }
            configs_summary[p_name] = summary

        # Compute paired statistical tests across presets on identical (task, seed) pairs
        stat_comparisons: dict[str, Any] = {}
        full_key = AgentConfigPreset.FULL.value
        p_values_to_correct: list[tuple[str, float]] = []

        if full_key in trials_by_preset:
            for other_key in [AgentConfigPreset.FIXED_RAG.value, AgentConfigPreset.BASIC.value]:
                if other_key in trials_by_preset:
                    # Match pairs by (task_id, seed)
                    pair_map_full = {
                        (t["task_id"], t["seed"]): t["tests_passed"]
                        for t in trials_by_preset[full_key]
                    }
                    pair_map_other = {
                        (t["task_id"], t["seed"]): t["tests_passed"]
                        for t in trials_by_preset[other_key]
                    }

                    shared_keys = sorted(set(pair_map_full.keys()) & set(pair_map_other.keys()))
                    full_outcomes = [pair_map_full[k] for k in shared_keys]
                    other_outcomes = [pair_map_other[k] for k in shared_keys]

                    mcn = mcnemar_test(full_outcomes, other_outcomes)
                    comp_id = f"full_vs_{other_key}"
                    stat_comparisons[comp_id] = {
                        "statistic": mcn.statistic,
                        "p_value": mcn.p_value,
                        "odds_ratio": mcn.odds_ratio,
                        "is_significant_nominal": mcn.is_significant,
                        "test_type": mcn.test_type,
                        "contingency_table": mcn.contingency_table,
                    }
                    p_values_to_correct.append((comp_id, mcn.p_value))

        # Apply Holm-Bonferroni correction to multiple comparisons
        if p_values_to_correct:
            raw_p = [p for _, p in p_values_to_correct]
            corrected = holm_bonferroni_correction(raw_p)
            for (comp_id, _), (_, adj_p, is_sig) in zip(
                p_values_to_correct, corrected, strict=True
            ):
                stat_comparisons[comp_id]["p_value_adjusted"] = adj_p
                stat_comparisons[comp_id]["is_significant_adjusted"] = is_sig

        final_report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "total_tasks": len(eval_tasks),
            "seeds": self.seeds,
            "configs": configs_summary,
            "statistical_comparisons": stat_comparisons,
            "raw_records": trials_by_preset,
        }

        # Save report JSON
        report_path = self.results_dir / "latest_evaluation_report.json"
        report_path.write_text(json.dumps(final_report, indent=2), encoding="utf-8")
        logger.info("eval_experiment_finished", report_path=str(report_path))

        return final_report
