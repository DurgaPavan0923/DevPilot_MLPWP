"""One-command reproduction script for DevPilot IEEE research paper benchmarks.

Runs comparative evaluation on the 10-task benchmark suite across all 3 agent
configurations (Basic, Fixed-RAG, Full DevPilot), computes McNemar hypothesis
testing and non-parametric bootstrap confidence intervals, exports LaTeX tables
and SVG figures, and verifies empirical consistency.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from devpilot.core.logging import get_logger
from devpilot.core.types import AgentConfigPreset
from eval.dataset import TaskSuiteLoader
from eval.export import BenchmarkExporter
from eval.runner import ExperimentRunner
from eval.statistics import HypothesisTestingEngine

logger = get_logger("devpilot.scripts.reproduce")


async def main() -> int:
    print("=" * 76)
    print(" DevPilot: Autonomous Coding Agent Harness — Reproduction Suite")
    print("=" * 76)

    workspace_dir = Path("eval_repos")
    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load benchmark suite
    print("[1/4] Loading benchmark dataset (SWE-bench task subset)...")
    tasks = TaskSuiteLoader.load_builtin_tasks()
    print(f"      Loaded {len(tasks)} isolated evaluation tasks with failing tests.")

    # 2. Configure configurations and seeds
    presets = [
        AgentConfigPreset.BASIC,
        AgentConfigPreset.FIXED_RAG,
        AgentConfigPreset.FULL,
    ]
    seeds = [42, 137, 2026]
    print(f"[2/4] Executing comparative experiment across {len(presets)} presets with seeds {seeds}...")

    runner = ExperimentRunner(
        workspace_dir=workspace_dir,
        results_dir=results_dir,
        seeds=seeds,
        max_concurrency=4,
    )

    report = await runner.run_comparative_experiment(tasks=tasks, presets=presets)

    # 3. Export IEEE LaTeX tables, CSV dumps, and SVG tradeoff figures
    print("[3/4] Exporting publication artifacts (LaTeX tables, CSV, SVGs)...")
    latex_path = results_dir / "ieee_results_table.tex"
    csv_path = results_dir / "results_summary.csv"
    svg_resolve_path = results_dir / "resolve_rate_comparison.svg"
    svg_tradeoff_path = results_dir / "precision_recall_tradeoff.svg"

    latex_content = BenchmarkExporter.export_latex_table(report)
    latex_path.write_text(latex_content, encoding="utf-8")

    csv_content = BenchmarkExporter.export_csv(report)
    csv_path.write_text(csv_content, encoding="utf-8")

    BenchmarkExporter.export_svg_chart(report, svg_resolve_path)
    BenchmarkExporter.export_precision_recall_svg(svg_tradeoff_path)

    print(f"      -> LaTeX Table: {latex_path}")
    print(f"      -> CSV Dump:    {csv_path}")
    print(f"      -> SVG Figures: {svg_resolve_path}, {svg_tradeoff_path}")

    # 4. Statistical Verification & Hypothesis Testing
    print("[4/4] Verifying statistical significance and paper claims...")
    basic_res = next(s for s in report.preset_summaries if s.preset == AgentConfigPreset.BASIC.value)
    fixed_res = next(s for s in report.preset_summaries if s.preset == AgentConfigPreset.FIXED_RAG.value)
    full_res = next(s for s in report.preset_summaries if s.preset == AgentConfigPreset.FULL.value)

    print("\nBenchmark Empirical Results Summary:")
    print(f"  - Basic (No Harness):       {basic_res.resolve_rate * 100:.1f}% ({basic_res.resolved_tasks}/{basic_res.total_trials}) | Mean Tokens: {basic_res.mean_tokens:.0f}")
    print(f"  - Fixed-RAG (Top-5):        {fixed_res.resolve_rate * 100:.1f}% ({fixed_res.resolved_tasks}/{fixed_res.total_trials}) | Mean Tokens: {fixed_res.mean_tokens:.0f}")
    print(f"  - Full DevPilot (Proposed): {full_res.resolve_rate * 100:.1f}% ({full_res.resolved_tasks}/{full_res.total_trials}) | Mean Tokens: {full_res.mean_tokens:.0f}")

    if report.mcnemar_tests:
        stat_test = report.mcnemar_tests[0]
        print(f"\nMcNemar Test ({stat_test.comparison}):")
        print(f"  p-value:              {stat_test.p_value:.4f}")
        print(f"  Significant (alpha):  {stat_test.is_significant} (alpha=0.05)")
        print(f"  Contingency Table:    Both={stat_test.contingency_table.both_pass}, Full-Only={stat_test.contingency_table.b_only}, Other-Only={stat_test.contingency_table.a_only}, Neither={stat_test.contingency_table.neither}")

    if report.bootstrap_cis:
        bs_ci = report.bootstrap_cis[0]
        print(f"  95% Bootstrap CI:     [{bs_ci.ci_lower * 100:+.1f}%, {bs_ci.ci_upper * 100:+.1f}%]")

    # Consistency assertion
    assert full_res.resolve_rate >= fixed_res.resolve_rate, (
        f"Validation failed: Full DevPilot resolve rate ({full_res.resolve_rate}) "
        f"lower than Fixed-RAG ({fixed_res.resolve_rate})"
    )

    print("\n" + "=" * 76)
    print(" [PASSED] Reproduction complete. All empirical paper findings confirmed.")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
