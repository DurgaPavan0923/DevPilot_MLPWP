# Threats to Validity in DevPilot Empirical Evaluation

In accordance with empirical software engineering guidelines (Wohlin et al., 2012; IEEE standards), this document formally itemizes the internal, external, construct, and conclusion threats to validity associated with the DevPilot evaluation framework and provides specific mitigation strategies.

---

## 1. Internal Validity (Causal Relationships and Confounding Factors)

### Threat 1.1: Data Leakage and Target Context Contamination
- **Risk**: If the agent harness has access to test patch files, gold patches, or commit messages containing solutions during context indexing or retrieval, the measured performance will be inflated and ungeneralizable.
- **Mitigation in DevPilot**:
  - `SWEBenchTask.to_benchmark_task` strips all references to `gold_patch` and `test_patch`.
  - The repository scanner and `PathSandbox` strictly enforce that test patches are held in an out-of-band evaluation harness directory and only applied after the agent runtime has signaled terminal state (`DONE`).
  - Pre-evaluation audit: unit test `test_data_leakage_prevention` guarantees that gold patch strings never appear in `retrieved_chunks`, `messages`, or `RetrievalTrace`.

### Threat 1.2: Confounding Prompt and Temperature Variations
- **Risk**: Differences in model prompts, temperature settings, or system instructions between configurations could obscure the actual impact of adaptive retrieval and structured recovery.
- **Mitigation in DevPilot**:
  - All configurations (`Basic`, `FixedTopK`, `AdaptiveHybrid`) share the identical system prompt template, tool definitions, FSM transitions, and LLM hyperparameters ($T=0.0$, top-p$=1.0$, fixed random seeds).
  - Only the retrieval mechanism and recovery feedback ladder vary between ablation conditions.

---

## 2. Construct Validity (Alignment Between Metrics and Real-world Quality)

### Threat 2.1: Test Suite Inadequacy and False Positives
- **Risk**: A task might be marked "resolved" if tests pass, even if the underlying bug was not properly resolved or if tests were trivially bypassed or deleted by the agent.
- **Mitigation in DevPilot**:
  - `VerificationRunner` verifies that existing test files were not modified or deleted by inspecting git diff against the base commit.
  - Test suites enforce both `fail-to-pass` (the bug is genuinely fixed) and `pass-to-pass` (no existing functionality was regressed).
  - Repositories without verified test suites return `UNVERIFIED` rather than falsely claiming success.

### Threat 2.2: Context Window Truncation Bias
- **Risk**: Simple truncation might drop critical early instructions, while uncompressed context might cause model degradation due to "lost in the middle" phenomena.
- **Mitigation in DevPilot**:
  - `ContextWindowManager` implements structured summarization: retains system prompt, user prompt, and recent $K$ turns, while condensing middle turns into a structured edits ledger.

---

## 3. External Validity (Generalizability of Results)

### Threat 3.1: Repository Diversity and Language Bias
- **Risk**: Evaluating solely on Python repositories might bias conclusions toward Python-specific AST and symbol characteristics.
- **Mitigation in DevPilot**:
  - Tree-sitter parsers and symbol extractors support Python, JavaScript/TypeScript, and Java.
  - Multi-language benchmark tasks (Python and JS/TS) are integrated into the evaluation suite.

### Threat 3.2: LLM Non-Determinism and Model Specificity
- **Risk**: Evaluation on a single LLM provider might reflect model-specific fine-tuning idiosyncrasies rather than harness efficacy.
- **Mitigation in DevPilot**:
  - Multi-provider architecture supports Claude 3.5 Sonnet, GPT-4o, DeepSeek V3, and local Ollama models.
  - Experiments are replicated across $N \ge 3$ random seeds with Holm-Bonferroni corrected paired statistics.

---

## 4. Conclusion Validity (Statistical Rigor)

### Threat 4.1: Low Sample Size and Asymptotic Assumptions
- **Risk**: Using asymptotic Chi-square McNemar tests when sample sizes or discordant pair counts are small ($b + c < 25$) yields inaccurate p-values and inflated Type I error.
- **Mitigation in DevPilot**:
  - `mcnemar_test` automatically switches to the exact two-sided binomial distribution when discordant pairs are below 25.
  - All continuous metrics (precision, recall, steps, cost) report 95% non-parametric bootstrap confidence intervals computed over 10,000 resamples.
  - Multiple comparisons across ablation conditions apply Holm-Bonferroni family-wise error rate corrections.
