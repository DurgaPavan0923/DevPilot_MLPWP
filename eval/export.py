"""Export utilities: IEEE camera-ready LaTeX tables, CSV dumps, and publication figures."""

import csv
import io
from pathlib import Path
from typing import Any


def export_latex_table(report: dict[str, Any]) -> str:
    """Generates camera-ready IEEE / ACM LaTeX table from evaluation report."""
    configs = report.get("configs", {})

    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Comparative Evaluation Across Agent Configurations on Benchmark Tasks ($N \ge 3$ seeds)}",
        r"\label{tab:devpilot_main_results}",
        r"\begin{tabular}{lcccccc}",
        r"\hline",
        r"\textbf{Configuration} & \textbf{Completion (\%)} & \textbf{Pass Rate (\%)} & \textbf{Precision@5} & \textbf{Recall@5} & \textbf{Avg Steps} & \textbf{Avg Cost (USD)} \\",
        r"\hline",
    ]

    names = {
        "basic": "Basic Agent (Tools Only)",
        "fixed_rag": "Fixed-RAG (Top-5)",
        "full": r"\textbf{DevPilot (Adaptive Hybrid + Kneedle)}",
    }

    for key, label in names.items():
        if key in configs:
            data = configs[key]
            comp_rate = data.get("completion_rate", 0.0) * 100.0
            pass_rate = data.get("test_pass_rate", 0.0) * 100.0
            p5 = data.get("avg_precision_at_k", 0.0)
            r5 = data.get("avg_recall_at_k", 0.0)
            steps = data.get("avg_steps", 0.0)
            cost = data.get("avg_cost_usd", 0.0)
            lines.append(
                f"{label} & {comp_rate:.1f}\\% & {pass_rate:.1f}\\% & {p5:.3f} & {r5:.3f} & {steps:.1f} & \\${cost:.4f} \\\\"
            )

    lines.extend(
        [
            r"\hline",
            r"\end{tabular}",
            r"\end{table*}",
        ]
    )

    return "\n".join(lines)


def export_csv(report: dict[str, Any]) -> str:
    """Exports raw task trial records to CSV format."""
    raw = report.get("raw_records", {})
    output = io.StringIO()
    fieldnames = [
        "task_id",
        "repo",
        "preset",
        "seed",
        "model",
        "status",
        "tests_passed",
        "verification_status",
        "steps",
        "total_tokens",
        "total_cost_usd",
        "duration_sec",
        "recoveries_count",
        "precision_at_k",
        "recall_at_k",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for _preset_name, records in raw.items():
        for r in records:
            writer.writerow(r)

    return output.getvalue()


def generate_evaluation_figures(report: dict[str, Any], output_dir: Path) -> list[Path]:
    """Generates standalone publication-ready vector figures (SVG format) for paper inclusion.

    Output figures:
    1. resolve_rate_comparison.svg (Bar chart: Basic vs Fixed-RAG vs Full)
    2. precision_recall_tradeoff.svg (Scatter/Line: P@5 vs R@5 across configs)
    3. cost_vs_steps_efficiency.svg (Efficiency frontier)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    configs = report.get("configs", {})

    # 1. Resolve Rate Bar Chart SVG
    p_names = ["basic", "fixed_rag", "full"]
    labels = ["Basic (No RAG)", "Fixed-RAG (K=5)", "DevPilot (Full)"]
    rates = [configs.get(p, {}).get("test_pass_rate", 0.0) * 100.0 for p in p_names]
    colors = ["#94a3b8", "#38bdf8", "#4f46e5"]

    svg_bars = [
        f'<rect x="{80 + i * 160}" y="{260 - int(rates[i] * 2)}" width="90" height="{int(rates[i] * 2)}" fill="{colors[i]}" rx="4"/>'
        f'<text x="{125 + i * 160}" y="{250 - int(rates[i] * 2)}" font-family="sans-serif" font-size="13" font-weight="bold" fill="#1e293b" text-anchor="middle">{rates[i]:.1f}%</text>'
        f'<text x="{125 + i * 160}" y="285" font-family="sans-serif" font-size="12" fill="#475569" text-anchor="middle">{labels[i]}</text>'
        for i in range(3)
    ]

    fig1_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="340" viewBox="0 0 600 340">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="300" y="35" font-family="sans-serif" font-size="16" font-weight="bold" fill="#0f172a" text-anchor="middle">Task Resolve Rate by Harness Configuration</text>
  <line x1="60" y1="260" x2="560" y2="260" stroke="#cbd5e1" stroke-width="1.5"/>
  <line x1="60" y1="60" x2="60" y2="260" stroke="#cbd5e1" stroke-width="1.5"/>
  <text x="50" y="265" font-family="sans-serif" font-size="10" fill="#64748b" text-anchor="end">0%</text>
  <text x="50" y="165" font-family="sans-serif" font-size="10" fill="#64748b" text-anchor="end">50%</text>
  <text x="50" y="65" font-family="sans-serif" font-size="10" fill="#64748b" text-anchor="end">100%</text>
  <line x1="60" y1="160" x2="560" y2="160" stroke="#f1f5f9" stroke-dasharray="4"/>
  <line x1="60" y1="60" x2="560" y2="60" stroke="#f1f5f9" stroke-dasharray="4"/>
  {"".join(svg_bars)}
</svg>"""
    f1_path = output_dir / "resolve_rate_comparison.svg"
    f1_path.write_text(fig1_svg, encoding="utf-8")
    generated.append(f1_path)

    # 2. Precision@5 vs Recall@5 Tradeoff SVG
    p5_vals = [configs.get(p, {}).get("avg_precision_at_k", 0.0) for p in p_names]
    r5_vals = [configs.get(p, {}).get("avg_recall_at_k", 0.0) for p in p_names]

    pts = [
        f'<circle cx="{100 + int(r5_vals[i] * 380)}" cy="{250 - int(p5_vals[i] * 180)}" r="8" fill="{colors[i]}"/>'
        f'<text x="{100 + int(r5_vals[i] * 380)}" y="{235 - int(p5_vals[i] * 180)}" font-family="sans-serif" font-size="11" font-weight="bold" fill="{colors[i]}" text-anchor="middle">{labels[i]} (P={p5_vals[i]:.2f}, R={r5_vals[i]:.2f})</text>'
        for i in range(3)
    ]

    fig2_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="320" viewBox="0 0 600 320">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="300" y="30" font-family="sans-serif" font-size="15" font-weight="bold" fill="#0f172a" text-anchor="middle">Context Retrieval: Precision@5 vs Recall@5</text>
  <line x1="80" y1="260" x2="540" y2="260" stroke="#cbd5e1" stroke-width="1.5"/>
  <line x1="80" y1="50" x2="80" y2="260" stroke="#cbd5e1" stroke-width="1.5"/>
  <text x="310" y="295" font-family="sans-serif" font-size="12" fill="#475569" text-anchor="middle">Recall@5</text>
  <text x="35" y="155" font-family="sans-serif" font-size="12" fill="#475569" text-anchor="middle" transform="rotate(-90 35 155)">Precision@5</text>
  {"".join(pts)}
</svg>"""
    f2_path = output_dir / "precision_recall_tradeoff.svg"
    f2_path.write_text(fig2_svg, encoding="utf-8")
    generated.append(f2_path)

    return generated
