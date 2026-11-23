# DevPilot System Architecture & Technical Specification

## 1. Architectural Philosophy & Research Objectives

DevPilot is a modular, repository-aware autonomous coding agent harness designed for rigorous empirical research on software repair reliability. Rather than training proprietary foundation models, DevPilot acts as an intermediate cognitive and operational harness between existing state-of-the-art LLMs (OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, DeepSeek Coder, Google Gemini, local Ollama) and real-world codebases.

The core research objective of DevPilot is evaluating:
1. **Adaptive-K Context Retrieval:** Whether dynamic knee-detection over multi-modal reciprocal-rank fused scores reduces prompt token bloat while boosting recall of bug-inducing files compared to fixed Top-K RAG.
2. **Structured Bounded Recovery:** Whether a 5-tier deterministic escalation ladder with checkpoint rollbacks mitigates autoregressive compounding errors and tool hallucination loops.
3. **Defense-in-Depth Sandboxing:** Whether layered containment (canonical path jail, AST command policy, Docker microVMs) allows safe autonomous execution of untrusted agent-generated code.

---

## 2. Component Class Diagram

```mermaid
classDiagram
    class AgentRuntime {
        +session_id: str
        +repo_root: Path
        +preset: AgentConfigPreset
        +fsm: AgentStateMachine
        +tool_registry: ToolRegistry
        +recovery_policy: RecoveryPolicy
        +retriever: Retriever
        +run_task(instruction: str) dict
        +resume() dict
        +rollback(snapshot_id: str) list
    }

    class AgentStateMachine {
        +current_state: AgentStateEnum
        +data: AgentExecutionData
        +transition(to_state: AgentStateEnum, reason: str)
        +is_terminal() bool
    }

    class Retriever {
        <<interface>>
        +retrieve(query: str) tuple[list[CodeChunk], RetrievalTrace]
    }

    class AdaptiveHybridRetriever {
        -chunks: list[CodeChunk]
        -bm25: LexicalRetriever
        -dense: DenseSemanticRetriever
        -graph: RepoDependencyGraph
        +retrieve(query: str) tuple[list[CodeChunk], RetrievalTrace]
    }

    class AdaptiveKSelector {
        +select_k(scores: list[float], min_k: int, max_k: int) int
    }

    class ToolRegistry {
        -tools: dict[str, BaseTool]
        +register(tool: BaseTool)
        +execute(name: str, args: dict) ToolResult
        +get_definitions() list[ToolDefinition]
    }

    class RecoveryPolicy {
        +total_recoveries: int
        +handle_tool_error(tool: str, args: dict, res: ToolResult) RecoveryAction
        +handle_verification_failure(test_output: str) RecoveryAction
    }

    class PathSandbox {
        +root: Path
        +resolve_safe_path(rel_path: str) Path
        +is_safe_path(target: Path) bool
    }

    class DockerExecutor {
        +image: str
        +mem_limit: str
        +cpu_limit: float
        +execute(cmd: str, cwd: str) ToolResult
    }

    AgentRuntime --> AgentStateMachine
    AgentRuntime --> Retriever
    AgentRuntime --> ToolRegistry
    AgentRuntime --> RecoveryPolicy
    Retriever <|.. AdaptiveHybridRetriever
    AdaptiveHybridRetriever --> AdaptiveKSelector
    ToolRegistry --> PathSandbox
    ToolRegistry --> DockerExecutor
```

---

## 3. End-to-End Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer / SWE-bench
    participant API as FastAPI / CLI
    participant RT as AgentRuntime
    participant FSM as StateMachine
    participant Ctx as AdaptiveHybridRetriever
    participant LLM as LLMProvider
    participant Tools as ToolRegistry & Sandbox
    participant Rec as RecoveryPolicy
    participant Ver as VerificationRunner

    Dev->>API: Launch Task (prompt, preset, repo)
    API->>RT: run_task(instruction)
    RT->>FSM: transition(ANALYZE)
    RT->>Ctx: scan & build AST index
    RT->>FSM: transition(RETRIEVE)
    Ctx->>Ctx: BM25 + Dense Embeddings + Graph Expansion
    Ctx->>Ctx: Reciprocal Rank Fusion & Adaptive-K Knee
    Ctx-->>RT: Context Chunks + RetrievalTrace
    
    loop ReAct Loop (Step <= max_steps, Cost <= budget)
        RT->>FSM: transition(PLAN)
        RT->>LLM: chat(system_prompt, context, messages)
        LLM-->>RT: Assistant Response (ToolCalls)
        
        alt Has Tool Calls
            RT->>FSM: transition(ACT)
            loop For Each Tool Call in Batch
                RT->>Tools: execute(tool_name, arguments)
                Tools-->>RT: ToolResult (ok, output, duration)
                
                alt Tool Failed
                    RT->>Rec: handle_tool_error(name, args, result)
                    Rec-->>RT: RecoveryAction (Level 1..5)
                    alt Level 3: Snapshot Rollback
                        RT->>Tools: rollback("baseline")
                    else Level 5: Abort
                        RT->>FSM: transition(FAILED)
                    end
                end
            end
            RT->>FSM: transition(OBSERVE)
        else No Tool Calls (Proposed Solution Reached)
            RT->>FSM: transition(VERIFY)
            RT->>Ver: run_verification(tests)
            alt Tests Pass
                Ver-->>RT: Verification Passed
                RT->>FSM: transition(DONE)
            else Tests Fail
                Ver-->>RT: Failure Diagnostics
                RT->>Rec: handle_verification_failure(output)
                Rec-->>RT: Replanning prompt with failing trace
                RT->>FSM: transition(PLAN)
            end
        end
    end

    RT-->>API: FinalReport (status, patch, metrics)
    API-->>Dev: Execution Complete & Diff Summary
```

---

## 4. Subsystem Specifications

### 4.1 LLM Provider Layer
- **Async Streaming Base (`LLMProvider`):** Abstract base class defining `chat()`, `chat_stream()`, `count_tokens()`, and `calculate_cost()`.
- **Supported Adapters:** Anthropic Claude (native tool calling with input schemas), OpenAI (function calling API), Google Gemini (Content parts and function declarations), DeepSeek (native chat format with caching tokens), Ollama (local open-weights models like Qwen2.5-Coder and Llama-3.1), and deterministic `MockProvider`.
- **JSON/XML Tool Calling Fallback:** Robust parser handling models lacking native tool APIs by extracting `<tool_call>` tags or markdown JSON codeblocks.
- **Resilience Engine:** Exponential backoff with jitter on HTTP 429/500/503 errors and sliding-window token bucket rate limiters.

### 4.2 Adaptive Context Engine
- **AST Parsing (`RepoIndex`):** Tree-sitter parsers for Python, JavaScript, TypeScript, and Java extracting function, class, and method symbols with line ranges.
- **Call & Dependency Graph (`RepoDependencyGraph`):** Directed network tracking file imports and class relationships with PageRank centrality and BFS neighbor expansion.
- **Fusion Calibration:** Dual min-max calibration normalizing BM25 lexical BM25 scores and cosine embeddings before applying weighted Reciprocal Rank Fusion ($k=60$):
  $$RRF\_Score(d) = \sum_{m \in \{lex, dense, graph\}} \frac{w_m}{k + r_m(d)}$$
- **Kneedle Knee Detection (`AdaptiveKSelector`):** Automatically computes the maximum difference between normalized cumulative score and diagonal line on the sorted RRF distribution curve, selecting the mathematical elbow point to prevent context pollution.

### 4.3 Tool Execution & Safety Architecture
- **Normalized Envelope (`ToolResult`):** Every tool execution returns a typed envelope with boolean success, string output, error classification, duration in milliseconds, process exit code, and truncation flag.
- **Canonical Workspace Jail (`PathSandbox`):** Enforces path resolution within repository boundaries, explicitly preventing NUL bytes, Windows double-backslash traversal (`..\\..\\`), and symbolic link escapes.
- **Command Whitelist (`CommandSecurityPolicy`):** Enforces tokenized command checking, blocking shell operators (`|`, `&`, `;`, `` ` ``, `$()`), path evasion tricks (`/bin/rm`), and dangerous system utilities.
- **Container Isolation (`DockerExecutor`):** Sandboxed container runner with read-only root filesystems, explicit memory (4GB) and CPU (2.0 cores) quotas, and no network egress (`network_mode="none"`).

### 4.4 Bounded Recovery Engine
- **Error Classifier:** Categorizes runtime exceptions into deterministic classes: `SYNTAX_ERROR`, `FILE_NOT_FOUND`, `PATCH_MISMATCH`, `PERMISSION_DENIED`, `TEST_FAILURE`, and `TIMEOUT`.
- **5-Tier Escalation Ladder:**
  - **Level 1 (Self-Correction):** Structured retry with targeted diagnostic error hints.
  - **Level 2 (Re-Retrieval):** Dynamic contextual re-indexing using failing symbols or stack traces.
  - **Level 3 (Approach Switch / Rollback):** Reverts dirty filesystem changes back to the pre-turn baseline snapshot.
  - **Level 4 (Alternative Tooling):** Switches tool modality (e.g. falling back from exact patch edit to file rewrite).
  - **Level 5 (Bounded Abort):** Safely terminates execution when retry caps or cost budgets are exceeded, preventing runaway API bills.
