export interface MockSession {
  id: string;
  status: "COMPLETED" | "FAILED" | "RUNNING" | "PAUSED" | "UNVERIFIED";
  preset: "basic" | "fixed_rag" | "full";
  provider: string;
  model: string;
  created_at: string;
  steps: number;
  total_tokens: number;
  total_cost_usd: number;
  task: string;
}

export const MOCK_SESSIONS: MockSession[] = [
  {
    id: "sess_demo_alpha_92",
    status: "COMPLETED",
    preset: "full",
    provider: "deepseek",
    model: "deepseek-coder",
    created_at: new Date(Date.now() - 1000 * 60 * 14).toISOString(),
    steps: 5,
    total_tokens: 38420,
    total_cost_usd: 0.0094,
    task: "Fix ZeroDivisionError when calculating average order value with empty cart items",
  },
  {
    id: "sess_demo_beta_41",
    status: "RUNNING",
    preset: "full",
    provider: "openai",
    model: "gpt-4o",
    created_at: new Date(Date.now() - 1000 * 60 * 3).toISOString(),
    steps: 3,
    total_tokens: 24150,
    total_cost_usd: 0.0412,
    task: "Implement bounded retry ladder with snapshot rollback in order processing pipeline",
  },
  {
    id: "sess_demo_gamma_18",
    status: "FAILED",
    preset: "basic",
    provider: "anthropic",
    model: "claude-3-5-sonnet-20241022",
    created_at: new Date(Date.now() - 1000 * 60 * 65).toISOString(),
    steps: 12,
    total_tokens: 61200,
    total_cost_usd: 0.1836,
    task: "Resolve race condition in payment state machine transitions under concurrent webhooks",
  },
  {
    id: "sess_demo_delta_05",
    status: "PAUSED",
    preset: "fixed_rag",
    provider: "gemini",
    model: "gemini-1.5-pro",
    created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    steps: 4,
    total_tokens: 19800,
    total_cost_usd: 0.0125,
    task: "Update authentication middleware to validate HMAC authorization header signatures",
  },
];

export interface MockAgentEvent {
  type: "STATE_CHANGE" | "THOUGHT" | "TOOL_CALL" | "TOOL_RESULT" | "RECOVERY" | "APPROVAL_REQUIRED" | "RETRIEVAL" | "FINAL";
  session_id: string;
  step: number;
  timestamp: string;
  data: Record<string, any>;
}

export const MOCK_EVENT_STREAM: MockAgentEvent[] = [
  {
    type: "STATE_CHANGE",
    session_id: "sess_demo_alpha_92",
    step: 0,
    timestamp: "11:20:01",
    data: { state: "ANALYZE", reason: "Beginning repository analysis and AST scanning" },
  },
  {
    type: "STATE_CHANGE",
    session_id: "sess_demo_alpha_92",
    step: 0,
    timestamp: "11:20:02",
    data: { state: "RETRIEVE", reason: "Adaptive hybrid retrieval query: ZeroDivisionError average order value" },
  },
  {
    type: "RETRIEVAL",
    session_id: "sess_demo_alpha_92",
    step: 0,
    timestamp: "11:20:03",
    data: {
      query: "ZeroDivisionError empty cart average order value",
      total_candidates: 34,
      fused_count: 5,
      adaptive_k: 3,
      ranked_files: ["src/billing/calculator.py", "tests/test_calculator.py", "src/models/cart.py"],
      scores: [0.92, 0.78, 0.44],
    },
  },
  {
    type: "STATE_CHANGE",
    session_id: "sess_demo_alpha_92",
    step: 1,
    timestamp: "11:20:04",
    data: { state: "PLAN", reason: "Analyzing retrieved context and formulating repair hypothesis" },
  },
  {
    type: "THOUGHT",
    session_id: "sess_demo_alpha_92",
    step: 1,
    timestamp: "11:20:05",
    data: {
      thought: "The error occurs at line 48 of src/billing/calculator.py when len(cart.items) == 0. A zero check must guard the division, returning Decimal('0.00') rather than throwing ZeroDivisionError.",
    },
  },
  {
    type: "STATE_CHANGE",
    session_id: "sess_demo_alpha_92",
    step: 1,
    timestamp: "11:20:06",
    data: { state: "ACT", reason: "Executing tool: read_file on src/billing/calculator.py" },
  },
  {
    type: "TOOL_CALL",
    session_id: "sess_demo_alpha_92",
    step: 1,
    timestamp: "11:20:06",
    data: {
      id: "call_read_01",
      name: "read_file",
      arguments: { path: "src/billing/calculator.py", start_line: 40, end_line: 60 },
    },
  },
  {
    type: "TOOL_RESULT",
    session_id: "sess_demo_alpha_92",
    step: 1,
    timestamp: "11:20:07",
    data: {
      tool_call_id: "call_read_01",
      tool_name: "read_file",
      ok: true,
      output: "40: def compute_order_average(cart: Cart) -> Decimal:\n41:     total = sum(i.price for i in cart.items)\n42:     count = len(cart.items)\n43:     return total / count",
      duration_ms: 12.4,
    },
  },
  {
    type: "STATE_CHANGE",
    session_id: "sess_demo_alpha_92",
    step: 2,
    timestamp: "11:20:08",
    data: { state: "ACT", reason: "Executing tool: edit_file on src/billing/calculator.py" },
  },
  {
    type: "TOOL_CALL",
    session_id: "sess_demo_alpha_92",
    step: 2,
    timestamp: "11:20:08",
    data: {
      id: "call_edit_02",
      name: "edit_file",
      arguments: {
        path: "src/billing/calculator.py",
        target: "    count = len(cart.items)\n    return total / count",
        replacement: "    count = len(cart.items)\n    if count == 0:\n        return Decimal('0.00')\n    return total / count",
      },
    },
  },
  {
    type: "TOOL_RESULT",
    session_id: "sess_demo_alpha_92",
    step: 2,
    timestamp: "11:20:09",
    data: {
      tool_call_id: "call_edit_02",
      tool_name: "edit_file",
      ok: true,
      output: "Successfully replaced 1 occurrence in src/billing/calculator.py",
      duration_ms: 18.1,
    },
  },
  {
    type: "STATE_CHANGE",
    session_id: "sess_demo_alpha_92",
    step: 3,
    timestamp: "11:20:10",
    data: { state: "ACT", reason: "Executing tool: run_tests" },
  },
  {
    type: "TOOL_CALL",
    session_id: "sess_demo_alpha_92",
    step: 3,
    timestamp: "11:20:10",
    data: {
      id: "call_test_03",
      name: "run_tests",
      arguments: { test_target: "tests/test_calculator.py" },
    },
  },
  {
    type: "TOOL_RESULT",
    session_id: "sess_demo_alpha_92",
    step: 3,
    timestamp: "11:20:12",
    data: {
      tool_call_id: "call_test_03",
      tool_name: "run_tests",
      ok: true,
      output: "================ 6 passed in 0.42s ================",
      duration_ms: 420.5,
    },
  },
  {
    type: "STATE_CHANGE",
    session_id: "sess_demo_alpha_92",
    step: 4,
    timestamp: "11:20:13",
    data: { state: "VERIFY", reason: "Automated regression verification check" },
  },
  {
    type: "STATE_CHANGE",
    session_id: "sess_demo_alpha_92",
    step: 5,
    timestamp: "11:20:14",
    data: { state: "DONE", reason: "All tests pass. Patch verified and committed." },
  },
  {
    type: "FINAL",
    session_id: "sess_demo_alpha_92",
    step: 5,
    timestamp: "11:20:14",
    data: {
      status: "COMPLETED",
      verification_status: "PASSED",
      steps: 5,
      modified_files: ["src/billing/calculator.py"],
      total_tokens: 38420,
      total_cost_usd: 0.0094,
      duration_sec: 14.2,
      recoveries_count: 0,
    },
  },
];

export const MOCK_DIFF_ORIGINAL = `def compute_order_average(cart: Cart) -> Decimal:
    """Computes the mean price across all items in cart."""
    total = sum(i.price for i in cart.items)
    count = len(cart.items)
    return total / count
`;

export const MOCK_DIFF_MODIFIED = `def compute_order_average(cart: Cart) -> Decimal:
    """Computes the mean price across all items in cart."""
    total = sum(i.price for i in cart.items)
    count = len(cart.items)
    if count == 0:
        return Decimal("0.00")
    return total / count
`;

export const MOCK_RETRIEVED_CHUNKS = [
  {
    file_path: "src/billing/calculator.py",
    symbol_name: "compute_order_average",
    chunk_type: "function",
    start_line: 40,
    end_line: 46,
    score: 0.9412,
    method: "AdaptiveHybrid (BM25: 0.42, Dense: 0.58)",
    code: `def compute_order_average(cart: Cart) -> Decimal:\n    total = sum(i.price for i in cart.items)\n    count = len(cart.items)\n    return total / count`,
  },
  {
    file_path: "tests/test_calculator.py",
    symbol_name: "test_empty_cart_average",
    chunk_type: "function",
    start_line: 18,
    end_line: 25,
    score: 0.8124,
    method: "Dense Semantic Embedding (cosine=0.86)",
    code: `def test_empty_cart_average():\n    cart = Cart(items=[])\n    # Expect zero rather than ZeroDivisionError\n    assert compute_order_average(cart) == Decimal("0.00")`,
  },
  {
    file_path: "src/models/cart.py",
    symbol_name: "Cart",
    chunk_type: "class",
    start_line: 12,
    end_line: 30,
    score: 0.6551,
    method: "Graph Expansion (1-hop inbound dependent)",
    code: `class Cart(BaseModel):\n    id: UUID\n    user_id: str\n    items: list[CartItem] = Field(default_factory=list)`,
  },
];

export const MOCK_EVAL_SUMMARY = {
  presets: [
    {
      preset: "Full DevPilot (AdaptiveHybrid + Bounded Recovery)",
      resolve_rate: 0.833,
      resolved_count: 25,
      total_count: 30,
      mean_tokens: 38420,
      mean_cost_usd: 0.0142,
      mean_duration_sec: 28.5,
    },
    {
      preset: "Fixed-RAG (Top-5 BM25/Dense)",
      resolve_rate: 0.633,
      resolved_count: 19,
      total_count: 30,
      mean_tokens: 49100,
      mean_cost_usd: 0.0215,
      mean_duration_sec: 41.2,
    },
    {
      preset: "Basic (No Retrieval Harness)",
      resolve_rate: 0.400,
      resolved_count: 12,
      total_count: 30,
      mean_tokens: 18400,
      mean_cost_usd: 0.0089,
      mean_duration_sec: 19.8,
    },
  ],
  statistical_significance: {
    comparison: "Full DevPilot vs Fixed-RAG",
    mcnemar_statistic: 4.5,
    p_value: 0.0339,
    is_significant: true,
    bootstrap_ci_95: [0.082, 0.324],
    contingency_table: {
      both_resolved: 18,
      full_only: 7,
      fixed_only: 1,
      both_failed: 4,
    },
  },
  task_matrix: [
    { id: "TASK-01", repo: "django/forms", basic: false, fixed_rag: true, full: true },
    { id: "TASK-02", repo: "requests/auth", basic: false, fixed_rag: false, full: true },
    { id: "TASK-03", repo: "flask/blueprints", basic: true, fixed_rag: true, full: true },
    { id: "TASK-04", repo: "scikit-learn/neighbors", basic: false, fixed_rag: true, full: true },
    { id: "TASK-05", repo: "pytest/assertion", basic: true, fixed_rag: true, full: true },
    { id: "TASK-06", repo: "sympy/matrices", basic: false, fixed_rag: false, full: true },
    { id: "TASK-07", repo: "pydantic/validators", basic: true, fixed_rag: true, full: true },
    { id: "TASK-08", repo: "astropy/coordinates", basic: false, fixed_rag: false, full: false },
    { id: "TASK-09", repo: "matplotlib/colors", basic: false, fixed_rag: true, full: true },
    { id: "TASK-10", repo: "sphinx/parser", basic: false, fixed_rag: false, full: true },
  ],
};
