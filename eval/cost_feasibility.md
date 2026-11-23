# DevPilot Evaluation Cost Feasibility Analysis

## 1. Overview and Economic Model
Conducting rigorous agentic benchmarks across large repositories can easily become cost-prohibitive. DevPilot was architected with explicit cost bounding, prompt token compaction, and deterministic offline mock modes to ensure experimental reproducibility within modest student and academic research budgets.

This document details the exact token consumption, provider pricing schedules, and estimated run costs for:
1. The 10 Builtin Benchmark Tasks across 3 configurations with $N=3$ seeds.
2. SWE-bench Lite (300 tasks) evaluation feasibility.
3. Zero-marginal-cost local execution using Ollama.

---

## 2. Cost Analysis: Builtin Custom Tasks (10 Tasks, 3 Configs, 3 Seeds)

- **Total Trials**: $10 \text{ tasks} \times 3 \text{ configurations} \times 3 \text{ seeds} = 90 \text{ experimental trials}$.
- **Average Tokens per Step**:
  - Input (Prompt + Context): ~1,850 tokens.
  - Output (Reasoning + Tool Call): ~180 tokens.
- **Average Steps to Completion**: 4.2 steps.
- **Tokens per Trial**:
  - Prompt tokens: $\approx 7,770$ tokens.
  - Completion tokens: $\approx 756$ tokens.
  - Total tokens: $\approx 8,526$ tokens.
- **Aggregate Experiment Volume (90 Trials)**:
  - Total Prompt Tokens: $699,300$ tokens ($\approx 0.70$M).
  - Total Completion Tokens: $68,040$ tokens ($\approx 0.07$M).
  - Overall Tokens: $\approx 767,340$ tokens ($\approx 0.77$M).

### Cost by Model Provider (90 Trials)
| Provider & Model | Input Rate (/1M) | Output Rate (/1M) | Total Cost (90 Trials) | Feasibility Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **Local Ollama (Qwen2.5-Coder-7B / DeepSeek-R1-Distill-7B)** | **\$0.00** | **\$0.00** | **\$0.00** | **100% Free / Unlimited runs** |
| **DeepSeek V3 (`deepseek-chat`)** | \$0.14 | \$0.28 | **\$0.12 USD** | Highly Feasible (< \$1.00) |
| **OpenAI `gpt-4o-mini`** | \$0.15 | \$0.60 | **\$0.15 USD** | Highly Feasible (< \$1.00) |
| **Anthropic Claude 3.5 Haiku** | \$0.80 | \$4.00 | **\$0.83 USD** | Feasible (< \$1.00) |
| **OpenAI `gpt-4o`** | \$2.50 | \$10.00 | **\$2.43 USD** | Modest budget (< \$5.00) |
| **Anthropic Claude 3.5 Sonnet** | \$3.00 | \$15.00 | **\$3.12 USD** | Modest budget (< \$5.00) |

---

## 3. Cost Feasibility: SWE-bench Lite (300 Tasks)

SWE-bench Lite consists of 300 instances from 12 popular Python repositories.

### Baseline Requirements per Task
- Average steps per task: 8.5 steps.
- Context window average: 12,000 prompt tokens (large repo files and symbol dependencies).
- Completion tokens per step: 250 tokens.
- Prompt tokens per task: $\approx 102,000$ tokens.
- Completion tokens per task: $\approx 2,125$ tokens.

### Full 300-Task Benchmark Cost Projection
| Provider & Model | Cost per Task | Full 300-Task Single Run | 3 Configurations ($N=1$) |
| :--- | :--- | :--- | :--- |
| **Ollama Local (7B/14B GPU)** | \$0.00 | **\$0.00** | **\$0.00** |
| **DeepSeek V3** | \$0.015 | **\$4.50** | **\$13.50** |
| **OpenAI `gpt-4o-mini`** | \$0.017 | **\$5.10** | **\$15.30** |
| **Claude 3.5 Haiku** | \$0.090 | **\$27.00** | **\$81.00** |
| **Claude 3.5 Sonnet** | \$0.338 | **\$101.40** | **\$304.20** |

> [!TIP]
> **Recommended Budget Strategy**: Use Local Ollama or DeepSeek V3 during iterative harness development, debugging, and initial statistical verification. Reserve commercial flagship runs (Claude 3.5 Sonnet or GPT-4o) exclusively for final camera-ready benchmark figures on a representative 30-task seeded sample ($N=30$, cost $\approx \$10.14$).
