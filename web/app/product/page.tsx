import React from "react";
import Link from "next/link";
import {
  Cpu,
  Database,
  Terminal,
  Layers,
  RotateCcw,
  ShieldCheck,
  Activity,
  ArrowRight,
  Code2,
  Lock,
  GitBranch,
  Play,
  Zap,
} from "lucide-react";

export default function ProductArchitecturePage() {
  const components = [
    {
      id: "llm-provider",
      num: "01",
      title: "LLM Provider Layer",
      icon: Cpu,
      package: "devpilot/llm/",
      interfaceName: "LLMProvider",
      summary:
        "Unified asynchronous interface supporting Anthropic, OpenAI, Gemini, DeepSeek, Ollama, and OpenAI-compatible providers.",
      details: [
        "Streaming response handling and token usage tracking via tiktoken and provider metadata.",
        "Cost accounting ledger enforcing step-level and session-level budget limits.",
        "Structured tool-calling abstraction with automatic JSON and XML schema fallback for models lacking native function calling.",
        "Exponential backoff with jitter for transient HTTP 429 and 503 provider errors.",
      ],
    },
    {
      id: "context-engine",
      num: "02",
      title: "Repository Analysis and Context Engine",
      icon: Database,
      package: "devpilot/repo/ & devpilot/context/",
      interfaceName: "RepoScanner, RepoIndex, HybridRetriever",
      summary:
        "Synthesizes lexical BM25 matching, dense vector embeddings, and AST symbol call graphs for repository context retrieval.",
      details: [
        "Tree-sitter AST symbol extraction for Python functions, classes, methods, and call sites.",
        "NetworkX directed dependency graph calculating PageRank importance and 1-hop topological neighbor expansion.",
        "Reciprocal Rank Fusion (RRF) combining sparse BM25 scores with dense vector similarities.",
        "Adaptive-K budget allocation with knee-detection curve filtering to eliminate prompt bloat.",
      ],
    },
    {
      id: "agent-runtime",
      num: "03",
      title: "Agent Runtime and Control Loop",
      icon: Terminal,
      package: "devpilot/agent/",
      interfaceName: "AgentRuntime, AgentState",
      summary:
        "Deterministic asynchronous finite-state machine coordinating analysis, planning, tool action, observation, and recovery.",
      details: [
        "Explicit FSM states: INIT, ANALYZE, PLAN, ACT, OBSERVE, RECOVER, VERIFY, DONE, FAILED.",
        "ReAct-style reasoning traces interleaved with structured tool invocations.",
        "Human-in-the-loop approval gating for interactive and auto-safe security modes.",
        "Real-time event dispatch emitting typed trace events over Server-Sent Events (SSE).",
      ],
    },
    {
      id: "tools-sandbox",
      num: "04",
      title: "Structured Tools and Execution Sandbox",
      icon: Layers,
      package: "devpilot/safety/ & devpilot/tools/",
      interfaceName: "BaseTool, DockerSandbox, WorkspaceJail",
      summary:
        "Guarded tool execution environment preventing path traversal, process escape, and arbitrary shell command injection.",
      details: [
        "Core primitives: read_file, edit_file, run_command, git_diff, revert_workspace.",
        "Docker container isolation with non-root user execution, memory limits, and CPU quotas.",
        "Workspace path jail resolving canonical paths and blocking symlink escape attempts.",
        "Command denylist blocking dangerous operations like fork bombs, raw disk access, and shell escapes.",
      ],
    },
    {
      id: "bounded-recovery",
      num: "05",
      title: "Feedback-Driven Bounded Recovery",
      icon: RotateCcw,
      package: "devpilot/agent/recovery.py",
      interfaceName: "ErrorClassifier, RecoveryEngine",
      summary:
        "Deterministic recovery subsystem preventing infinite failure loops when tools fail or tests break.",
      details: [
        "Regex and AST error classifier categorizing syntax errors, runtime exceptions, test failures, and permission denials.",
        "Targeted recovery prompts advising the LLM on corrective steps based on error taxonomy.",
        "Strict recovery attempt budget (default: maximum 3 recovery steps per sub-task).",
        "Clean workspace rollback to the last verified git baseline snapshot when recovery budget is exhausted.",
      ],
    },
    {
      id: "verification-engine",
      num: "06",
      title: "Automated Verification Engine",
      icon: ShieldCheck,
      package: "devpilot/verification/",
      interfaceName: "VerificationEngine, TestRunner",
      summary:
        "Rigorous pre-patch and post-patch validation ensuring proposed code edits solve target issues without regressions.",
      details: [
        "Baseline verification: executes test suites prior to modifications to record expected initial failures.",
        "Post-patch validation: re-runs test suites in isolated sandbox environments to confirm test resolution.",
        "AST syntax verification ensuring code edits do not introduce invalid syntax or broken imports.",
        "Clean patch export: generates unified git diffs ready for review or benchmark submission.",
      ],
    },
    {
      id: "session-store",
      num: "07",
      title: "Session Persistence and REST API",
      icon: Activity,
      package: "devpilot/session/ & devpilot/api/",
      interfaceName: "SessionStore, FastAPI Router",
      summary:
        "Persistent SQLite session ledger and REST API powering dashboard telemetry, replay, and human oversight.",
      details: [
        "Complete event audit trail: logs all thoughts, tool calls, tool results, diffs, and costs in SQLite.",
        "FastAPI backend exposing session lifecycle, repository inspection, and evaluation management endpoints.",
        "Streaming SSE endpoint (/api/sessions/{id}/events) for real-time live execution updates.",
        "Human approval webhook (/api/sessions/{id}/approval) for interactive permission elevation.",
      ],
    },
  ];

  return (
    <div className="space-y-12 pb-16">
      {/* Header */}
      <div className="border-b border-white/[0.08] pb-8 max-w-4xl space-y-4">
        <div className="inline-flex items-center space-x-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs font-mono font-medium text-violet-300">
          <Code2 className="h-3.5 w-3.5" />
          <span>SYSTEM ARCHITECTURE BLUEPRINT</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
          DevPilot Architecture Overview
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          DevPilot is structured into 7 decoupled subsystems. Each component is defined behind an abstract Python interface, allowing independent evaluation, substitution, and rigorous ablation benchmarking.
        </p>

        <div className="pt-2 flex items-center space-x-3 text-xs">
          <Link
            href="/sessions"
            className="inline-flex items-center space-x-1.5 rounded-md bg-violet-600 px-4 py-2 font-semibold text-white hover:bg-violet-500 transition"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            <span>Launch Live Session</span>
          </Link>
          <Link
            href="/repo"
            className="inline-flex items-center space-x-1.5 rounded-md border border-white/[0.1] bg-[#0D1220] px-4 py-2 font-medium text-slate-200 hover:text-white transition"
          >
            <GitBranch className="h-3.5 w-3.5 text-cyan-400" />
            <span>Repository Call Graph</span>
          </Link>
        </div>
      </div>

      {/* Component Cards */}
      <div className="space-y-6">
        {components.map((c) => {
          const Icon = c.icon;
          return (
            <div
              key={c.id}
              id={c.id}
              className="rounded-md border border-white/[0.08] bg-[#0D1220] p-6 space-y-4 shadow-sm hover:border-violet-500/30 transition"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-white/[0.08]">
                <div className="flex items-center space-x-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-md bg-violet-500/15 text-violet-400 border border-violet-500/25 shrink-0">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <span className="font-mono text-xs text-violet-400 mr-2">{c.num}.</span>
                    <h2 className="inline text-base font-bold text-white">{c.title}</h2>
                  </div>
                </div>
                <div className="flex items-center space-x-2 font-mono text-[11px]">
                  <span className="rounded border border-white/[0.1] bg-[#080B14] px-2.5 py-0.5 text-cyan-300">
                    {c.package}
                  </span>
                  <span className="rounded border border-white/[0.1] bg-[#121A2A] px-2.5 py-0.5 text-slate-300">
                    {c.interfaceName}
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-200 font-medium leading-relaxed">
                {c.summary}
              </p>

              <div className="space-y-2 pt-2">
                <h3 className="text-[10px] font-mono font-semibold text-muted-foreground uppercase tracking-wider">
                  Technical Specifications & Capabilities
                </h3>
                <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-300">
                  {c.details.map((detail, dIdx) => (
                    <li key={dIdx} className="flex items-start space-x-2 bg-[#080B14] p-2.5 rounded border border-white/[0.04]">
                      <span className="h-1.5 w-1.5 rounded-full bg-violet-400 shrink-0 mt-1.5" />
                      <span>{detail}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
