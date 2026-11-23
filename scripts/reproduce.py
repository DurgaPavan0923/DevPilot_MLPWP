"""Reproduction script for DevPilot comparative evaluation benchmarks.

Runs comparative evaluation on benchmark suites across agent configurations
(Basic, Fixed-RAG, Full DevPilot), computes McNemar hypothesis tests and
non-parametric bootstrap confidence intervals, and exports LaTeX tables, CSV dumps,
and tradeoff figures.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from devpilot.config import get_settings
from devpilot.core.logging import get_logger
from devpilot.core.types import AgentConfigPreset
from devpilot.llm.factory import create_provider
from eval.dataset import TaskSuiteLoader
from eval.export import export_csv, export_latex_table, generate_evaluation_figures
from eval.runner import ExperimentRunner

logger = get_logger("devpilot.scripts.reproduce")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DevPilot Comparative Evaluation and Reproduction Harness"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=os.getenv("DEVPILOT_PROVIDER", None),
        help="LLM provider name (e.g., 'deepseek', 'openai', 'anthropic', 'ollama', 'mock').",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("DEVPILOT_MODEL", None),
        help="Model identifier (e.g., 'deepseek-coder', 'gpt-4o', 'claude-3-5-sonnet').",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="42,137,2026",
        help="Comma-separated random seeds for multi-seed replication (default: '42,137,2026').",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Maximum concurrent evaluation task workers (default: 4).",
    )
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        help="Explicitly permit execution with MockProvider for harness validation and pipeline testing.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("eval/results"),
        help="Directory to save evaluation reports and export artifacts (default: eval/results).",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    settings = get_settings()

    provider_name = (args.provider or settings.llm.default_provider).lower().strip()
    model_name = args.model or settings.llm.default_model

    print("=" * 76)
    print(" DevPilot: Autonomous Coding Agent Harness — Reproduction Suite")
    print("=" * 76)
    print(f"Target LLM Provider: {provider_name} (model: {model_name})")

    # Safety gate against claiming mock test results as real research findings
    if provider_name == "mock" and not args.allow_mock:
        print("\n" + "!" * 76)
        print(" [SAFETY BLOCK] Mock provider detected ('mock').")
        print(" Running evaluation with MockProvider tests harness mechanics and event flow,")
        print(" but does NOT perform real neural code generation, reasoning, or debugging.")
        print()
        print(" To run empirical research evaluations against real models:")
        print("     python scripts/reproduce.py --provider deepseek --model deepseek-coder")
        print("     python scripts/reproduce.py --provider openai --model gpt-4o")
        print(" or configure DEVPILOT_PROVIDER and DEVPILOT_MODEL in your environment.")
        print()
        print(" To run a pipeline smoke test with the mock provider anyway, pass '--allow-mock'.")
        print("!" * 76 + "\n")
        return 1

    try:
        seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    except ValueError:
        print(f"Error: Invalid seeds specification: {args.seeds}")
        return 1

    workspace_dir = Path("eval_repos")
    results_dir = args.results_dir
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load benchmark suite
    print(f"\n[1/4] Loading benchmark dataset (Builtin task suite, seeds={seeds})...")
    tasks = TaskSuiteLoader.load_builtin_tasks()
    print(f"      Loaded {len(tasks)} isolated evaluation tasks with failing tests.")

    # 2. Configure configurations and seeds
    presets = [
        AgentConfigPreset.BASIC,
        AgentConfigPreset.FIXED_RAG,
        AgentConfigPreset.FULL,
    ]
    print(f"[2/4] Executing comparative experiment across {len(presets)} presets...")
    if provider_name == "mock":
        print("      (NOTE: Running in MOCK mode with --allow-mock. Measurements are simulated.)")

    llm_instance = create_provider(provider_name=provider_name, model=model_name)

    runner = ExperimentRunner(
        workspace_dir=workspace_dir,
        results_dir=results_dir,
        llm=llm_instance,
        seeds=seeds,
        max_concurrency=args.concurrency,
    )

    report: dict[str, Any] = await runner.run_comparative_experiment(tasks=tasks, presets=presets)

    # 3. Export publication artifacts
    print("[3/4] Exporting publication artifacts (LaTeX tables, CSV, SVGs)...")
    latex_path = results_dir / "ieee_results_table.tex"
    csv_path = results_dir / "results_summary.csv"

    latex_content = export_latex_table(report)
    latex_path.write_text(latex_content, encoding="utf-8")

    csv_content = export_csv(report)
    csv_path.write_text(csv_content, encoding="utf-8")

    generated_svgs = generate_evaluation_figures(report, results_dir)

    print(f"      -> LaTeX Table: {latex_path}")
    print(f"      -> CSV Dump:    {csv_path}")
    for svg_f in generated_svgs:
        print(f"      -> SVG Figure:  {svg_f}")

    # 4. Statistical Verification & Hypothesis Testing Reporting
    print("\n[4/4] Empirical Measurement Summary:")
    configs = report.get("configs", {})
    for p_key, p_data in configs.items():
        pass_rate = p_data.get("test_pass_rate", 0.0) * 100.0
        comp_rate = p_data.get("completion_rate", 0.0) * 100.0
        avg_tokens = p_data.get("avg_tokens", 0.0)
        avg_cost = p_data.get("avg_cost_usd", 0.0)
        avg_dur = p_data.get("avg_duration_sec", 0.0)
        print(
            f"  - {p_key:<20}: "
            f"Pass Rate: {pass_rate:.1f}% | "
            f"Completion: {comp_rate:.1f}% | "
            f"Mean Tokens: {avg_tokens:.0f} | "
            f"Mean Cost: ${avg_cost:.4f} | "
            f"Mean Time: {avg_dur:.1f}s"
        )

    stat_comps = report.get("statistical_comparisons", {})
    if stat_comps:
        print("\nStatistical Significance Tests:")
        for comp_name, comp_data in stat_comps.items():
            p_val = comp_data.get("p_value", 1.0)
            p_adj = comp_data.get("p_value_adjusted", p_val)
            is_sig = comp_data.get("is_significant_nominal", False)
            table = comp_data.get("contingency_table", {})
            print(f"  - {comp_name}:")
            print(f"      p-value (raw):      {p_val:.4f}")
            print(f"      p-value (adjusted): {p_adj:.4f}")
            print(f"      Nominal Sig (a=0.05): {is_sig}")
            print(f"      Contingency Table:  {table}")

    print("\n" + "=" * 76)
    if provider_name == "mock":
        print(" [COMPLETE] Mock pipeline test completed successfully.")
        print(
            "            Official empirical findings require execution with real LLM credentials."
        )
    else:
        print(" [COMPLETE] Reproduction run finished. Artifacts saved to eval/results.")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
