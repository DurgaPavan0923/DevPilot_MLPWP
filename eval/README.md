# DevPilot Evaluation and Statistical Benchmarking Framework

The `eval/` package provides a reproducible comparative evaluation harness designed to empirically evaluate the core research question:

> **Research Question:** *Do adaptive repository-aware context retrieval and structured execution feedback improve the reliability, precision, and efficiency of autonomous coding agents on real software repositories?*

---

## 1. Architecture and Design

The evaluation framework operates completely decoupled from the agent runtime and backend server. It systematically evaluates coding agent performance across three controlled experimental configurations on identical task distributions and random seeds.

```
+-------------------------------------------------------------------------------+
|                             Evaluation Harness                                 |
+-------------------------------------------------------------------------------+
|  Dataset Loader                                                               |
|  - Built-in Benchmark Tasks (10 isolated repository defect scenarios)         |
|  - SWE-bench Lite / Verified Loader (git commit checkouts + fail_to_pass)     |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
|  Experiment Runner (eval/runner.py)                                           |
|  - Parallel execution worker pool with semaphore concurrency control          |
|  - Isolated tempdir repository checkouts per trial                            |
|  - Result caching (results/eval_results_cache.json) to eliminate duplicate calls|
|  - Per-task cost caps and wall-clock timeouts                                 |
+-------------------------------------------------------------------------------+
                                      |
         +----------------------------+----------------------------+
         v                                                         v
+-------------------------------+                         +---------------------+
| Metrics Engine (eval/metrics) |                         | Statistical Testing |
| - Test pass / resolve rate    |                         | (eval/statistics)   |
| - Retrieval Precision@K       |                         | - McNemar exact     |
| - Retrieval Recall@K          |                         | - Holm-Bonferroni   |
| - Step count & token usage    |                         | - 10k Bootstrap CI  |
+-------------------------------+                         +---------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Publication Exporters (eval/export.py)                                        |
| - IEEE camera-ready LaTeX tables (\begin{table*} ... \end{table*})            |
| - Raw CSV trial exports (results/results_summary.csv)                         |
| - Publication vector SVG figures (output_images/resolve_rate_comparison.svg)  |
+-------------------------------------------------------------------------------+
```

---

## 2. Experimental Configurations (Presets)

Every evaluation experiment executes across three controlled agent configurations:

| Configuration | Retrieval Strategy | Context Budget ($K$) | Recovery Ladder | Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Basic** | None (Tools only: `list_dir`, `read_file`) | N/A | Single retry | Exit code check |
| **Fixed-RAG** | Lexical BM25 + Dense Semantic Cosine | Fixed $K=5$ chunks | Bounded retry ladder | Automated pytest |
| **Full DevPilot** | Hybrid BM25 + Dense + AST Graph Expansion (RRF) | **Adaptive-K** (Kneedle elbow detection + task budget packing) | Bounded ladder + snapshot rollback | Automated test verification + audit report |

---

## 3. Statistical Testing Methodology

To guarantee scientific reproducibility and defend against stochastic noise in LLM evaluations, the framework incorporates formal non-parametric hypothesis tests:

1. **Paired McNemar Test**:
   Evaluates paired binary outcomes on identical task instances and seeds. Calculates exact binomial p-values when discordant pairs $b + c < 25$, and continuity-corrected $\chi^2$ statistics for larger sample sizes:
   $$\chi^2 = \frac{(|b - c| - 1)^2}{b + c}$$

2. **Holm-Bonferroni Multiplicity Correction**:
   Controls the Family-Wise Error Rate ($\text{FWER} \le 0.05$) across all pairwise comparisons (Full vs Basic, Full vs Fixed-RAG, Fixed-RAG vs Basic).

3. **Non-Parametric Bootstrap Confidence Intervals**:
   Computes 95% confidence intervals on $\Delta \text{Resolve Rate}$ using $B = 10{,}000$ bootstrap resamples with replacement.

---

## 4. Running Benchmarks

### A. Pipeline Validation / Smoke Mode (Mock LLM)
To verify the execution harness, filesystem isolation, git checkout mechanisms, and metric aggregators without consuming LLM credits:

```bash
python scripts/reproduce.py --allow-mock --concurrency 4
```

### B. Frontier Model Benchmark Run
To execute empirical paper evaluations against live foundation models:

```bash
# DeepSeek Coder
python scripts/reproduce.py --provider deepseek --model deepseek-coder --seeds 42,137,2026 --concurrency 4

# OpenAI GPT-4o
python scripts/reproduce.py --provider openai --model gpt-4o --seeds 42,137,2026 --concurrency 4

# Anthropic Claude 3.5 Sonnet
python scripts/reproduce.py --provider anthropic --model claude-3-5-sonnet-20241022 --seeds 42,137,2026
```

### C. CLI Evaluation Command
You can also run benchmarks using the primary `devpilot` CLI tool:

```bash
# Run 1 task with 1 seed across all presets
devpilot eval --suite builtin --seeds 42 --max-tasks 1 --allow-mock

# Full benchmark evaluation
devpilot eval --suite builtin --seeds 42,137,2026 --concurrency 4
```

---

## 5. Generated Artifacts

Results are automatically saved to `results/` and `output_images/`:
- `results/latest_evaluation_report.json`: Complete machine-readable trial records, raw outputs, and test statistics.
- `results/ieee_results_table.tex`: Ready-to-paste LaTeX table for academic manuscripts.
- `results/results_summary.csv`: Tabular spreadsheet for Pandas or R data analysis.
- `output_images/resolve_rate_comparison.svg`: Vector graphic bar chart of resolve rates by configuration.
- `output_images/precision_recall_tradeoff.svg`: Precision@K versus Recall@K Pareto curve.
