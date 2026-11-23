"""Unit tests for Evaluation Framework: metrics, SWE-bench loader, exact McNemar, Holm, exports, and figures."""

from pathlib import Path

import pytest

from eval.dataset import (
    TaskSuiteLoader,
    ensure_eval_repos,
)
from eval.export import export_csv, export_latex_table, generate_evaluation_figures
from eval.metrics import compute_retrieval_metrics
from eval.runner import ExperimentRunner
from eval.statistics import (
    bootstrap_confidence_interval,
    holm_bonferroni_correction,
    mcnemar_test,
)


def test_precision_recall_at_k():
    gold = ["src/auth.py", "src/models/user.py"]
    retrieved = [
        "src/auth.py",
        "src/utils.py",
        "src/models/user.py",
        "README.md",
        "tests/test_auth.py",
    ]

    # Precision@3: 2 hits out of 3 = 0.6667
    m3 = compute_retrieval_metrics(retrieved, gold, k=3)
    assert m3.precision_at_k == 0.6667
    # Recall@3: 2 hits out of 2 gold = 1.0
    assert m3.recall_at_k == 1.0

    # Precision@5: 2 hits out of 5 = 0.4000
    m5 = compute_retrieval_metrics(retrieved, gold, k=5)
    assert m5.precision_at_k == 0.4000
    assert m5.recall_at_k == 1.0


def test_mcnemar_statistical_test_exact_binomial():
    # Discordant pairs: b=10, c=1 (total discordant = 11 < 25 -> exact binomial test)
    outcomes_a = [True] * 10 + [False] * 1 + [True] * 5
    outcomes_b = [False] * 10 + [True] * 1 + [True] * 5

    res = mcnemar_test(outcomes_a, outcomes_b)
    assert res.test_type == "exact_binomial"
    assert res.p_value < 0.05
    assert res.is_significant is True
    assert res.contingency_table["b"] == 10
    assert res.contingency_table["c"] == 1


def test_mcnemar_statistical_test_asymptotic():
    # Discordant pairs: b=25, c=5 (total discordant = 30 >= 25 -> asymptotic Chi-square)
    outcomes_a = [True] * 25 + [False] * 5
    outcomes_b = [False] * 25 + [True] * 5

    res = mcnemar_test(outcomes_a, outcomes_b)
    assert res.test_type == "asymptotic_chisq"
    assert res.statistic > 0.0
    assert res.p_value < 0.05
    assert res.is_significant is True


def test_holm_bonferroni_correction():
    # Ordered p-values
    p_vals = [0.005, 0.01, 0.04, 0.10]
    corrected = holm_bonferroni_correction(p_vals)
    # Check that adjusted p-values are weakly monotonically increasing
    for i in range(len(corrected) - 1):
        assert corrected[i][1] <= corrected[i + 1][1]
    # Smallest p-value multiplied by m=4: 0.005 * 4 = 0.02
    assert corrected[0][1] == pytest.approx(0.02)
    assert corrected[0][2] is True


def test_bootstrap_confidence_interval():
    data = [10.0, 12.0, 11.5, 9.8, 12.2, 10.5, 11.0, 10.8]
    mean, lower, upper = bootstrap_confidence_interval(data, n_bootstrap=1000, ci=0.95, seed=42)

    assert 9.0 <= lower <= mean
    assert mean <= upper <= 13.0


def test_builtin_task_suite_loader():
    tasks = TaskSuiteLoader.load_builtin_tasks()
    assert len(tasks) == 10
    t0 = tasks[0]
    assert t0.task_id == "DP-001"
    assert len(t0.gold_files) > 0


def test_ensure_eval_repos(tmp_path: Path):
    created = ensure_eval_repos(tmp_path)
    assert len(created) == 10
    # Verify Task 1 contains code with real failing test
    r1 = created["task_01_auth_ttl"]
    assert (r1 / "src" / "jwt_helper.py").exists()
    assert (r1 / "tests" / "test_jwt.py").exists()


def test_swe_bench_lite_loader_leakage_prevention(tmp_path: Path):
    # Create sample SWE-bench Lite JSON file
    sample_data = [
        {
            "instance_id": "django__django-11099",
            "repo": "django/django",
            "base_commit": "abc123456",
            "problem_statement": "UsernameValidator accepts trailing newline in ASCII usernames.",
            "gold_patch": "diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py...",
            "test_patch": "diff --git a/tests/auth_tests/test_validators.py b/tests/auth_tests/test_validators.py...",
            "version": "lite",
            "fail_to_pass": ["test_ascii_trailing_newline"],
            "pass_to_pass": ["test_valid_usernames"],
        }
    ]
    swe_file = tmp_path / "swe_bench_lite.json"
    import json

    swe_file.write_text(json.dumps(sample_data), encoding="utf-8")

    loaded_swe = TaskSuiteLoader.load_swe_bench_lite(swe_file, sample_size=1)
    assert len(loaded_swe) == 1
    bench_task = loaded_swe[0].to_benchmark_task()

    # Data leakage check: gold_patch and test_patch MUST NOT be in BenchmarkTask instruction or gold_files
    assert "diff --git" not in bench_task.instruction
    assert bench_task.gold_files == []
    assert bench_task.instruction == sample_data[0]["problem_statement"]


def test_latex_and_csv_table_export():
    sample_report = {
        "configs": {
            "basic": {
                "completion_rate": 0.45,
                "test_pass_rate": 0.40,
                "avg_precision_at_k": 0.20,
                "avg_recall_at_k": 0.35,
                "avg_steps": 12.0,
                "avg_cost_usd": 0.05,
            },
            "fixed_rag": {
                "completion_rate": 0.65,
                "test_pass_rate": 0.60,
                "avg_precision_at_k": 0.45,
                "avg_recall_at_k": 0.55,
                "avg_steps": 9.5,
                "avg_cost_usd": 0.04,
            },
            "full": {
                "completion_rate": 0.85,
                "test_pass_rate": 0.80,
                "avg_precision_at_k": 0.72,
                "avg_recall_at_k": 0.82,
                "avg_steps": 6.8,
                "avg_cost_usd": 0.03,
            },
        },
        "raw_records": {
            "full": [
                {
                    "task_id": "DP-001",
                    "repo": "task_01_auth_ttl",
                    "preset": "full",
                    "seed": 42,
                    "model": "mock",
                    "status": "COMPLETED",
                    "tests_passed": True,
                    "verification_status": "VERIFIED",
                    "steps": 4,
                    "total_tokens": 1200,
                    "total_cost_usd": 0.01,
                    "duration_sec": 1.2,
                    "recoveries_count": 0,
                    "precision_at_k": 1.0,
                    "recall_at_k": 1.0,
                }
            ]
        },
    }
    latex = export_latex_table(sample_report)
    assert r"\begin{table*}" in latex
    assert "DevPilot" in latex
    assert r"85.0\%" in latex

    csv_data = export_csv(sample_report)
    assert "task_id,repo,preset,seed,model" in csv_data
    assert "DP-001,task_01_auth_ttl,full,42" in csv_data


def test_generate_evaluation_figures(tmp_path: Path):
    sample_report = {
        "configs": {
            "basic": {
                "test_pass_rate": 0.40,
                "avg_precision_at_k": 0.30,
                "avg_recall_at_k": 0.40,
            },
            "fixed_rag": {
                "test_pass_rate": 0.60,
                "avg_precision_at_k": 0.55,
                "avg_recall_at_k": 0.65,
            },
            "full": {"test_pass_rate": 0.85, "avg_precision_at_k": 0.78, "avg_recall_at_k": 0.88},
        }
    }
    output_dir = tmp_path / "figures"
    fig_paths = generate_evaluation_figures(sample_report, output_dir)
    assert len(fig_paths) == 2
    for p in fig_paths:
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "<svg" in content


@pytest.mark.asyncio
async def test_experiment_runner(tmp_path: Path):
    from devpilot.core.types import AgentConfigPreset

    runner = ExperimentRunner(
        workspace_dir=tmp_path,
        results_dir=tmp_path / "results",
        seeds=[42],
        max_concurrency=2,
    )
    tasks = TaskSuiteLoader.load_builtin_tasks(sample_size=1)
    report = await runner.run_comparative_experiment(
        tasks=tasks,
        presets=[AgentConfigPreset.BASIC, AgentConfigPreset.FULL],
    )

    assert "configs" in report
    assert "statistical_comparisons" in report
    assert (tmp_path / "results" / "latest_evaluation_report.json").exists()
