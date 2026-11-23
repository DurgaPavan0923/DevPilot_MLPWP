# DevPilot Empirical Evaluation Methodology & Benchmark Specification

## 1. Research Motivation & Core Hypothesis

Autonomous coding agents frequently suffer from two fundamental failure modes:
1. **Context Smog & Hallucination:** Naive lexical search or rigid Top-K RAG floods the context window with irrelevant files, exhausting token budgets and confusing model reasoning.
2. **Autoregressive Compounding Error:** When an initial edit fails or tests break, agents without structured recovery enter cascading error loops, repeatedly trying invalid patches.

**Primary Hypothesis ($H_1$):** A coding agent equipped with Adaptive-K Reciprocal Rank Fusion retrieval and a 5-tier structured bounded recovery ladder achieves a statistically significantly higher bug-resolution rate ($p < 0.05$) with lower mean token consumption than fixed Top-K and un-harnessed agents.

---

## 2. Experimental Design & Configuration Baselines

We evaluate three controlled agent harness configurations across identical benchmark task distributions:

| Configuration ID | Retrieval Modality | Context Sizing | Recovery Mechanism | Safety Sandbox |
| :--- | :--- | :--- | :--- | :--- |
| **Config A (Basic)** | No Retrieval | Zero pre-retrieved context | Unstructured text feedback | Active |
| **Config B (Fixed-RAG)** | BM25 + Dense Embeddings | Fixed Top-5 Chunks | Single-turn retry | Active |
| **Config C (Full DevPilot)** | AdaptiveHybrid (BM25 + Dense + Graph) | Kneedle Knee Detection | 5-Tier Bounded Escalation Ladder | Active |

**Controlled Invariants:**
- Foundation Model: `deepseek-coder` (or `mock-model` in offline deterministic CI).
- Temperature: 0.0 (deterministic greed decoding).
- Resource Ceilings: Step Cap = 20, Wall-Clock Timeout = 300s, Cost Ceiling = $0.50.
- Repetitions: 3 independent random seeds ($42, 137, 2026$) per task, generating $N = 30$ independent experimental trials.

---

## 3. Benchmark Dataset & Leakage Prevention

### 3.1 SWE-bench Task Subset
The benchmark suite comprises 10 isolated software engineering repositories with authentic bug reports and reproducible pytest harnesses (covering Python web frameworks, algorithmic utilities, and data pipelines).

### 3.2 Data Leakage Prevention
To guarantee scientific validity, the `SWEBenchTask` loader enforces strict leakage filtering:
- The reference `gold_patch` and `test_patch` are strictly stripped from all prompt contexts and filesystem structures accessible to the agent.
- Verification tests are run out-of-band by the `VerificationRunner` using isolated git checkouts.

---

## 4. Evaluation Metrics & Statistical Framework

### 4.1 Quantitative Performance Metrics
1. **Resolve Rate ($RR$):** Percentage of trials where the generated patch causes all failing unit tests to pass without breaking pre-existing regression suites:
   $$RR = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\text{status}_i = \text{COMPLETED} \land \text{tests\_pass}_i)$$
2. **Mean Token Expenditure ($\bar{T}$):** Sum of prompt and completion tokens per task trial.
3. **Mean Wall-Clock Latency ($\bar{D}$):** Total end-to-end execution duration in seconds.
4. **Mean Financial Cost ($\bar{C}$):** Total USD expenditure calculated against published provider pricing schedules.
5. **Precision@K & Recall@K:** Lexical and semantic retrieval accuracy benchmarked against known ground-truth modified files.

### 4.2 Statistical Significance & Hypothesis Testing
- **Exact Two-Sided McNemar Test:** Evaluates paired nominal outcomes between configurations on identical tasks. For discordant pairs $b$ (Full resolves, Fixed fails) and $c$ (Fixed resolves, Full fails):
  $$\text{If } (b + c) < 25: \quad p = 2 \sum_{k=0}^{\min(b,c)} \binom{b+c}{k} 0.5^{b+c}$$
  $$\text{If } (b + c) \ge 25: \quad \chi^2 = \frac{(|b - c| - 1)^2}{b + c}, \quad \text{df} = 1$$
- **Non-Parametric Bootstrap Confidence Intervals:** 10,000 resamples with replacement compute the 95% empirical confidence interval for the resolve rate difference $\Delta RR = RR_{\text{Full}} - RR_{\text{Fixed}}$.
- **Holm-Bonferroni Correction:** Multi-comparison step-down adjustment controlling the Family-Wise Error Rate (FWER) across pairwise comparisons.

---

## 5. Threats to Validity

1. **Construct Validity:** Resolved test suites approximate real-world correctness. We mitigate test-overfitting by executing comprehensive pre-existing regression test suites in addition to bug-specific assertions.
2. **Internal Validity:** LLM non-determinism is mitigated by freezing temperature to 0.0 and evaluating across 3 distinct seeds. Concurrency race conditions are eliminated through isolated temporary directory workspaces per trial.
3. **External Validity:** The benchmark evaluates Python codebases. While tree-sitter parsers support TypeScript, Java, and JavaScript, broader cross-language benchmarks represent valuable future work.
