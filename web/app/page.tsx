"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Play,
  Activity,
  DollarSign,
  Cpu,
  Clock,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  PauseCircle,
  Loader2,
  Layers,
  Database,
  Terminal,
  RotateCcw,
  BookOpen,
  Sparkles,
  GitBranch,
  Lock,
  Code2,
  BarChart3,
  Server,
  Zap,
  ChevronRight,
  Search,
  FileCode,
  ShieldAlert,
} from "lucide-react";
import { fetchSessions, createSession } from "@/lib/api";
import { formatUSD, formatNumber } from "@/lib/utils";
import type { MockSession } from "@/lib/mock-data";

interface PipelineStage {
  id: string;
  name: string;
  fsmState: string;
  icon: any;
  subsystem: string;
  module: string;
  action: string;
  detail: string;
  metric: string;
}

const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: "analysis",
    name: "Repository Analysis",
    fsmState: "ANALYZE",
    icon: Database,
    subsystem: "Context Engine",
    module: "devpilot/repo/ast_scanner.py",
    action: "Extracting AST call graphs and symbol tables via tree-sitter",
    detail: "Scanned 14 source files, discovered 84 functions, computed PageRank node centrality.",
    metric: "14 files indexed",
  },
  {
    id: "retrieval",
    name: "Context Retrieval",
    fsmState: "RETRIEVE",
    icon: Search,
    subsystem: "Hybrid Retriever",
    module: "devpilot/context/hybrid.py",
    action: "Reciprocal Rank Fusion of BM25 lexical scores and dense vector cosine similarity",
    detail: "Candidate pool of 34 chunks ranked. Adaptive-K knee curve selected top 5 high-relevance chunks.",
    metric: "Top-5 chunks (Knee-curve)",
  },
  {
    id: "planning",
    name: "Planning",
    fsmState: "PLAN",
    icon: Terminal,
    subsystem: "Agent Runtime",
    module: "devpilot/agent/runtime.py",
    action: "Formulating multi-step patch strategy and test plan",
    detail: "Isolated bug trigger to cart.py line 48. Plan: guard empty item division with default fallback.",
    metric: "3 planned sub-actions",
  },
  {
    id: "execution",
    name: "Tool Execution",
    fsmState: "ACT",
    icon: Layers,
    subsystem: "Execution Sandbox",
    module: "devpilot/safety/sandbox.py",
    action: "Executing unified diff patch inside isolated workspace sandbox jail",
    detail: "Applied 4-line patch to src/billing/calculator.py. Docker container enforced network egress deny.",
    metric: "Jail isolation ACTIVE",
  },
  {
    id: "observation",
    name: "Observation",
    fsmState: "OBSERVE",
    icon: Activity,
    subsystem: "Telemetry Store",
    module: "devpilot/session/store.py",
    action: "Collecting tool stdout, stderr, and file system diff changes",
    detail: "Patch applied cleanly with zero rejection chunks. Recorded git snapshot sha a7b841.",
    metric: "0 patch rejections",
  },
  {
    id: "recovery",
    name: "Bounded Recovery",
    fsmState: "RECOVER",
    icon: RotateCcw,
    subsystem: "Recovery Ladder",
    module: "devpilot/agent/recovery.py",
    action: "Monitoring execution anomalies and managing snapshot rollbacks",
    detail: "Error classifier armed with 3-retry ceiling. Snapshot rollback verified ready if tests fail.",
    metric: "0 / 3 retries used",
  },
  {
    id: "verification",
    name: "Verification",
    fsmState: "VERIFY",
    icon: ShieldCheck,
    subsystem: "Verification Engine",
    module: "devpilot/verification/runner.py",
    action: "Running automated pre-patch and post-patch pytest test suite",
    detail: "Executed pytest tests/test_calculator.py. 14 passed, 0 failed. Syntax validation confirmed.",
    metric: "14 / 14 tests passing",
  },
  {
    id: "completion",
    name: "Completion",
    fsmState: "DONE",
    icon: CheckCircle2,
    subsystem: "Session Store",
    module: "devpilot/session/store.py",
    action: "Persisting final session trace and updating token/cost ledger",
    detail: "Task completed successfully. Patch verified. Total tokens: 38,420 ($0.0094 inference cost).",
    metric: "Status: COMPLETED",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<MockSession[]>([]);
  const [loading, setLoading] = useState(true);

  // Interactive Pipeline State
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const [autoPlay, setAutoPlay] = useState(false);

  // Selected Architecture Component
  const [selectedSubsystem, setSelectedSubsystem] = useState<string>("llm-provider");

  // Form states
  const [taskInstruction, setTaskInstruction] = useState("");
  const [repoPath, setRepoPath] = useState(".");
  const [preset, setPreset] = useState("full");
  const [provider, setProvider] = useState("deepseek");
  const [model, setModel] = useState("deepseek-coder");
  const [permissionMode, setPermissionMode] = useState("auto_safe");
  const [launching, setLaunching] = useState(false);

  useEffect(() => {
    fetchSessions().then((data) => {
      setSessions(data);
      setLoading(false);
    });
  }, []);

  // Auto-play interactive pipeline
  useEffect(() => {
    if (!autoPlay) return;
    const interval = setInterval(() => {
      setActiveStageIndex((prev) => (prev + 1) % PIPELINE_STAGES.length);
    }, 2800);
    return () => clearInterval(interval);
  }, [autoPlay]);

  const handleLaunch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskInstruction.trim()) return;

    setLaunching(true);
    try {
      const res = await createSession({
        task: taskInstruction,
        preset,
        provider,
        model,
        permission_mode: permissionMode,
      });
      router.push(`/sessions/${res.id}`);
    } catch (err) {
      console.error(err);
      setLaunching(false);
    }
  };

  const totalCost = sessions.reduce((acc, s) => acc + s.total_cost_usd, 0);
  const activeCount = sessions.filter((s) => s.status === "RUNNING").length;
  const completedCount = sessions.filter((s) => s.status === "COMPLETED").length;

  const currentStage = PIPELINE_STAGES[activeStageIndex];
  const StageIcon = currentStage.icon;

  const subsystems = [
    {
      id: "llm-provider",
      num: "01",
      title: "LLM Provider Layer",
      icon: Cpu,
      package: "devpilot/llm/",
      interface: "LLMProvider",
      summary: "Unified asynchronous interface across OpenAI, Anthropic, Gemini, DeepSeek, and Ollama.",
      responsibilities: [
        "Async token streaming and token accounting ledger.",
        "Structured tool calling abstraction with automatic JSON/XML fallback.",
        "Provider rate limit handling with jittered exponential backoff.",
      ],
      connections: ["Agent Runtime", "Session Store"],
    },
    {
      id: "context-engine",
      num: "02",
      title: "Adaptive Repository Context Engine",
      icon: Database,
      package: "devpilot/repo/ & devpilot/context/",
      interface: "RepoScanner, HybridRetriever",
      summary: "Combines lexical BM25, dense embeddings, and AST symbol graphs for context retrieval.",
      responsibilities: [
        "Tree-sitter AST symbol indexing for functions, classes, and call sites.",
        "PageRank-weighted directed dependency graphs for neighbor expansion.",
        "Reciprocal Rank Fusion (RRF) with adaptive knee-curve budgeting.",
      ],
      connections: ["Agent Runtime", "Tools and Sandbox"],
    },
    {
      id: "agent-runtime",
      num: "03",
      title: "Autonomous Agent Runtime",
      icon: Terminal,
      package: "devpilot/agent/",
      interface: "AgentRuntime, AgentState",
      summary: "Finite-state machine governing the autonomous plan, act, observe, and verify control loop.",
      responsibilities: [
        "Deterministic FSM with states INIT, ANALYZE, PLAN, ACT, OBSERVE, VERIFY, DONE, FAILED.",
        "Human-in-the-loop approval gating for sensitive operations.",
        "Step budgeting and cycle-detection guarding against infinite agent loops.",
      ],
      connections: ["LLM Provider", "Context Engine", "Tools Sandbox", "Bounded Recovery"],
    },
    {
      id: "sandbox",
      num: "04",
      title: "Secure Execution Sandbox",
      icon: Layers,
      package: "devpilot/safety/",
      interface: "Sandbox, CommandPolicy",
      summary: "Hermetic tool and command execution with strict path jail and network isolation.",
      responsibilities: [
        "Workspace path containment preventing symlink escapes and directory traversal.",
        "Denylist command filter rejecting dangerous shell operations and fork bombs.",
        "Docker container isolation with CPU, memory, and egress limits.",
      ],
      connections: ["Agent Runtime", "Bounded Recovery"],
    },
    {
      id: "bounded-recovery",
      num: "05",
      title: "Bounded Error Recovery",
      icon: RotateCcw,
      package: "devpilot/agent/recovery.py",
      interface: "RecoveryEngine, SnapshotManager",
      summary: "Self-healing loop with syntax, runtime, test, and permission error classification.",
      responsibilities: [
        "Error classification mapping tracebacks to targeted repair strategies.",
        "Clean git snapshot rollbacks to restore baseline when patches fail.",
        "Strict bounded retry ceiling preventing token exhaustion and thrashing.",
      ],
      connections: ["Agent Runtime", "Verification Engine"],
    },
    {
      id: "verification",
      num: "06",
      title: "Automated Verification Engine",
      icon: ShieldCheck,
      package: "devpilot/verification/",
      interface: "VerificationRunner, DiffVerifier",
      summary: "Automated pre-patch and post-patch test execution to confirm genuine bug resolution.",
      responsibilities: [
        "Automated pytest test suite execution and syntax tree validation.",
        "Zero-regression verification against unchanged test suites.",
        "Clean unified diff generation and patch safety auditing.",
      ],
      connections: ["Bounded Recovery", "Session Store"],
    },
    {
      id: "session-store",
      num: "07",
      title: "Persistent Session Management",
      icon: Activity,
      package: "devpilot/session/ & devpilot/api/",
      interface: "SessionStore, SSEBroadcaster",
      summary: "SQLite trace persistence, FastAPI REST endpoints, and Server-Sent Events streaming.",
      responsibilities: [
        "Atomic SQLite event log storing state changes, thoughts, tool calls, and diffs.",
        "Real-time Server-Sent Events (SSE) telemetry broadcast to web clients.",
        "Historical session replay and comparative benchmark telemetry export.",
      ],
      connections: ["Agent Runtime", "Verification Engine", "Web UI"],
    },
  ];

  const activeSubsystem = subsystems.find((s) => s.id === selectedSubsystem) || subsystems[0];
  const SubsystemIcon = activeSubsystem.icon;

  return (
    <div className="space-y-16 pb-12">
      {/* Hero Section */}
      <section className="relative pt-6 pb-12 border-b border-white/[0.08]">
        <div className="max-w-4xl space-y-5">
          <div className="inline-flex items-center space-x-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs font-mono font-medium text-violet-300 shadow-sm shadow-violet-500/10">
            <span className="flex h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
            <span>AUTONOMOUS CODING AGENT HARNESS</span>
          </div>

          <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-6xl leading-[1.1]">
            Engineering Intelligence for Autonomous Software Development.
          </h1>

          <p className="text-lg leading-relaxed text-slate-300 max-w-3xl">
            DevPilot understands your repository, retrieves the right context, executes code in a secure environment, recovers from failures and verifies every change.
          </p>

          <div className="flex flex-wrap items-center gap-3.5 pt-2">
            <Link
              href="/sessions"
              className="inline-flex items-center space-x-2 rounded-md bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-violet-600/30 hover:bg-violet-500 transition active:scale-[0.98]"
            >
              <Play className="h-4 w-4 fill-current" />
              <span>Launch Workspace</span>
            </Link>

            <Link
              href="/product"
              className="inline-flex items-center space-x-2 rounded-md border border-white/[0.12] bg-[#0D1220] px-5 py-2.5 text-sm font-medium text-slate-200 hover:text-white hover:bg-white/[0.06] transition"
            >
              <Code2 className="h-4 w-4 text-violet-400" />
              <span>Explore Architecture</span>
            </Link>

            <Link
              href="/docs"
              className="inline-flex items-center space-x-1.5 rounded-md border border-white/[0.08] bg-transparent px-4 py-2.5 text-sm font-medium text-slate-400 hover:text-slate-200 transition"
            >
              <BookOpen className="h-4 w-4" />
              <span>Documentation</span>
            </Link>
          </div>

          {/* Technical Status Indicators */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-white/[0.08]">
            <div className="rounded-md border border-white/[0.06] bg-[#0D1220]/60 p-2.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground block">
                Subsystems
              </span>
              <span className="text-sm font-bold font-mono text-white mt-0.5 block">
                7 Modular Units
              </span>
            </div>

            <div className="rounded-md border border-white/[0.06] bg-[#0D1220]/60 p-2.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground block">
                Supported LLMs
              </span>
              <span className="text-sm font-bold font-mono text-white mt-0.5 block">
                5 Providers + Ollama
              </span>
            </div>

            <div className="rounded-md border border-white/[0.06] bg-[#0D1220]/60 p-2.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground block">
                Evaluation Presets
              </span>
              <span className="text-sm font-bold font-mono text-white mt-0.5 block">
                Full, Fixed-RAG, Basic
              </span>
            </div>

            <div className="rounded-md border border-white/[0.06] bg-[#0D1220]/60 p-2.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground block">
                State Machine
              </span>
              <span className="text-sm font-bold font-mono text-emerald-400 mt-0.5 block">
                Bounded Recovery
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Execution Pipeline Visualization */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2 text-violet-400 text-xs font-mono uppercase tracking-wider">
              <Zap className="h-3.5 w-3.5" />
              <span>Interactive Pipeline Preview</span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white mt-1">
              End-to-End Autonomous Execution Pipeline
            </h2>
            <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
              From raw bug reports to verified patch commits: select any stage to inspect active subroutines, AST analysis, and safety gating.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-mono text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded">
              SIMULATED PIPELINE TRACE
            </span>
            <button
              onClick={() => setAutoPlay(!autoPlay)}
              className="inline-flex items-center space-x-1.5 rounded-md border border-white/[0.1] bg-[#0D1220] px-3 py-1 text-xs font-medium text-slate-300 hover:text-white hover:border-violet-500/40 transition"
            >
              {autoPlay ? <PauseCircle className="h-3.5 w-3.5 text-violet-400" /> : <Play className="h-3.5 w-3.5 text-cyan-400" />}
              <span>{autoPlay ? "Pause Auto-Step" : "Auto-Step"}</span>
            </button>
          </div>
        </div>

        {/* Pipeline Stage Buttons */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {PIPELINE_STAGES.map((stage, idx) => {
            const Icon = stage.icon;
            const isSelected = idx === activeStageIndex;
            const isPast = idx < activeStageIndex;

            return (
              <button
                key={stage.id}
                onClick={() => {
                  setActiveStageIndex(idx);
                  setAutoPlay(false);
                }}
                className={`relative flex flex-col items-start p-3 rounded-md border text-left transition-all ${
                  isSelected
                    ? "border-violet-500/60 bg-violet-500/10 shadow-sm shadow-violet-500/20"
                    : isPast
                    ? "border-emerald-500/30 bg-[#0D1220] text-slate-300"
                    : "border-white/[0.06] bg-[#0D1220]/60 text-muted-foreground hover:border-white/[0.15]"
                }`}
              >
                <div className="flex items-center justify-between w-full mb-2">
                  <span className="font-mono text-[10px] text-muted-foreground">
                    0{idx + 1}
                  </span>
                  <div
                    className={`h-5 w-5 rounded flex items-center justify-center ${
                      isSelected
                        ? "bg-violet-500 text-white"
                        : isPast
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "bg-white/[0.05] text-muted-foreground"
                    }`}
                  >
                    <Icon className="h-3 w-3" />
                  </div>
                </div>
                <span className={`text-xs font-semibold leading-tight ${isSelected ? "text-white" : "text-slate-300"}`}>
                  {stage.name}
                </span>
                <span className="text-[10px] font-mono mt-1 text-muted-foreground truncate w-full">
                  {stage.fsmState}
                </span>

                {isSelected && (
                  <div className="absolute -bottom-1 left-3 right-3 h-0.5 bg-gradient-to-r from-violet-500 to-cyan-400 rounded-full" />
                )}
              </button>
            );
          })}
        </div>

        {/* Live Stage Detail Inspection Box */}
        <div className="rounded-md border border-white/[0.08] bg-[#0D1220] p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.08]">
            <div className="flex items-center space-x-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-violet-500/20 text-violet-300 border border-violet-500/30">
                <StageIcon className="h-4 w-4" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-bold text-white">
                    Stage {activeStageIndex + 1}: {currentStage.name}
                  </h3>
                  <span className="rounded bg-violet-500/15 border border-violet-500/30 px-2 py-0.5 text-[10px] font-mono font-bold text-violet-300">
                    {currentStage.fsmState}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground font-mono">
                  Subsystem: {currentStage.subsystem} ({currentStage.module})
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <span className="rounded border border-white/[0.1] bg-[#121A2A] px-2.5 py-1 text-xs font-mono text-cyan-300">
                {currentStage.metric}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-4 text-xs">
            <div className="md:col-span-7 space-y-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground block">
                Active Routine
              </span>
              <p className="text-slate-200 font-medium leading-relaxed">
                {currentStage.action}
              </p>
              <div className="p-3 rounded bg-[#080B14] border border-white/[0.06] font-mono text-[11px] text-slate-300 leading-relaxed">
                {currentStage.detail}
              </div>
            </div>

            <div className="md:col-span-5 space-y-2 border-t md:border-t-0 md:border-l border-white/[0.08] md:pl-4 pt-3 md:pt-0">
              <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground block">
                Subsystem Linkage
              </span>
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between py-1 border-b border-white/[0.04]">
                  <span className="text-muted-foreground">Component:</span>
                  <span className="text-white font-medium">{currentStage.subsystem}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/[0.04]">
                  <span className="text-muted-foreground">Source Module:</span>
                  <code className="text-violet-300 font-mono text-[11px]">{currentStage.module}</code>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Security Mode:</span>
                  <span className="text-emerald-400 font-mono">Path Jail Active</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 7 Modular Subsystems Feature Showcase */}
      <section className="space-y-6">
        <div>
          <div className="flex items-center space-x-2 text-violet-400 text-xs font-mono uppercase tracking-wider">
            <Layers className="h-3.5 w-3.5" />
            <span>Architecture Specification</span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white mt-1">
            7 Modular Subsystems
          </h2>
          <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
            Every component sits behind an abstract interface, enabling independent benchmarking, swappable components, and strict isolation.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {subsystems.map((sub) => {
            const Icon = sub.icon;
            return (
              <div
                key={sub.id}
                className="group relative rounded-md border border-white/[0.08] bg-[#0D1220] p-5 space-y-3 hover:border-violet-500/40 hover:bg-[#121A2A] transition-all"
              >
                <div className="flex items-center justify-between">
                  <div className="flex h-8 w-8 items-center justify-center rounded bg-violet-500/10 text-violet-400 border border-violet-500/20 group-hover:bg-violet-500/20 group-hover:text-violet-300 transition">
                    <Icon className="h-4 w-4" />
                  </div>
                  <span className="font-mono text-xs text-muted-foreground">
                    {sub.num}
                  </span>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-white group-hover:text-violet-200 transition">
                    {sub.title}
                  </h3>
                  <code className="text-[10px] text-muted-foreground font-mono block mt-0.5">
                    {sub.package}
                  </code>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">
                  {sub.summary}
                </p>

                <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-[11px]">
                  <span className="font-mono text-violet-400 text-[10px] truncate max-w-[180px]">
                    {sub.interface}
                  </span>
                  <Link
                    href={`/product#${sub.id}`}
                    className="inline-flex items-center space-x-1 text-slate-400 hover:text-white transition font-medium"
                  >
                    <span>Inspect</span>
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Interactive Subsystem Topology / Architecture Graph */}
      <section className="space-y-6">
        <div>
          <div className="flex items-center space-x-2 text-violet-400 text-xs font-mono uppercase tracking-wider">
            <GitBranch className="h-3.5 w-3.5" />
            <span>Interactive Subsystem Inspector</span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white mt-1">
            System Topology and Data Contracts
          </h2>
          <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
            Select any subsystem node below to inspect its data flow contracts, interface boundaries, and connected components.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Subsystem Node List */}
          <div className="lg:col-span-5 space-y-2">
            {subsystems.map((sub) => {
              const Icon = sub.icon;
              const isSelected = sub.id === selectedSubsystem;
              return (
                <button
                  key={sub.id}
                  onClick={() => setSelectedSubsystem(sub.id)}
                  className={`w-full flex items-center justify-between p-3 rounded-md border text-left transition-all ${
                    isSelected
                      ? "border-violet-500/60 bg-violet-500/10 text-white shadow-sm shadow-violet-500/10"
                      : "border-white/[0.06] bg-[#0D1220] text-slate-300 hover:border-white/[0.15] hover:bg-[#121A2A]"
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div
                      className={`h-7 w-7 rounded flex items-center justify-center ${
                        isSelected
                          ? "bg-violet-500 text-white"
                          : "bg-white/[0.05] text-muted-foreground"
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5" />
                    </div>
                    <div>
                      <span className="text-xs font-semibold block">{sub.title}</span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {sub.package}
                      </span>
                    </div>
                  </div>
                  <ChevronRight className={`h-4 w-4 ${isSelected ? "text-violet-400" : "text-muted-foreground"}`} />
                </button>
              );
            })}
          </div>

          {/* Subsystem Topology Card */}
          <div className="lg:col-span-7 rounded-md border border-white/[0.08] bg-[#0D1220] p-6 space-y-5">
            <div className="flex items-center justify-between pb-4 border-b border-white/[0.08]">
              <div className="flex items-center space-x-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-md bg-violet-500/20 text-violet-300 border border-violet-500/30">
                  <SubsystemIcon className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">{activeSubsystem.title}</h3>
                  <code className="text-xs font-mono text-cyan-300">{activeSubsystem.interface}</code>
                </div>
              </div>
              <span className="font-mono text-xs text-muted-foreground">
                Node {activeSubsystem.num} / 07
              </span>
            </div>

            <div className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground block">
                Primary Responsibilities
              </span>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {activeSubsystem.responsibilities.map((resp, i) => (
                  <li key={i} className="flex items-start space-x-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{resp}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="space-y-2 pt-3 border-t border-white/[0.06]">
              <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground block">
                Connected Downstream / Upstream Subsystems
              </span>
              <div className="flex flex-wrap gap-2">
                {activeSubsystem.connections.map((conn, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center space-x-1.5 rounded border border-violet-500/30 bg-violet-500/10 px-2.5 py-1 text-xs font-mono text-violet-300"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-violet-400" />
                    <span>{conn}</span>
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Link
                href={`/product#${activeSubsystem.id}`}
                className="inline-flex items-center space-x-1.5 rounded-md bg-white/[0.06] border border-white/[0.1] px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-white/[0.1] transition"
              >
                <span>Read Technical Specs</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Operational Metrics Cards (Real Session Store Data) */}
      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-white">Live Session Store Metrics</h2>
          <p className="text-xs text-muted-foreground">
            Operational activity aggregated directly from the local SQLite persistent database.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-md border border-white/[0.08] bg-[#0D1220] p-4">
            <span className="text-xs font-medium text-muted-foreground">Persisted Sessions</span>
            <div className="mt-2 text-2xl font-bold font-mono text-white">{sessions.length}</div>
            <p className="mt-1 text-[11px] text-muted-foreground font-mono">SQLite atomic store</p>
          </div>

          <div className="rounded-md border border-white/[0.08] bg-[#0D1220] p-4">
            <span className="text-xs font-medium text-muted-foreground">Active Tasks</span>
            <div className="mt-2 text-2xl font-bold font-mono text-cyan-400">{activeCount}</div>
            <p className="mt-1 text-[11px] text-muted-foreground font-mono">Running FSM runtime</p>
          </div>

          <div className="rounded-md border border-white/[0.08] bg-[#0D1220] p-4">
            <span className="text-xs font-medium text-muted-foreground">Completed Tasks</span>
            <div className="mt-2 text-2xl font-bold font-mono text-emerald-400">{completedCount}</div>
            <p className="mt-1 text-[11px] text-muted-foreground font-mono">Verified patch resolutions</p>
          </div>

          <div className="rounded-md border border-white/[0.08] bg-[#0D1220] p-4">
            <span className="text-xs font-medium text-muted-foreground">Tracked Inference Cost</span>
            <div className="mt-2 text-2xl font-bold font-mono text-white">{formatUSD(totalCost)}</div>
            <p className="mt-1 text-[11px] text-muted-foreground font-mono">Pricing ledger tokens</p>
          </div>
        </div>
      </section>

      {/* Main Grid: Launcher + Recent Sessions */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Launcher Form */}
        <div className="lg:col-span-5 rounded-md border border-white/[0.08] bg-[#0D1220] p-5 space-y-4">
          <div className="flex items-center space-x-2 pb-3 border-b border-white/[0.08]">
            <Play className="h-4 w-4 text-violet-400" />
            <h2 className="text-sm font-semibold text-white">Launch Agent Task</h2>
          </div>

          <form onSubmit={handleLaunch} className="space-y-3.5">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Task Instruction or Bug Report
              </label>
              <textarea
                required
                rows={3}
                value={taskInstruction}
                onChange={(e) => setTaskInstruction(e.target.value)}
                placeholder="e.g. Fix ZeroDivisionError when calculating average order value with empty cart items..."
                className="w-full rounded-md border border-white/[0.1] bg-[#080B14] p-2.5 text-xs text-white placeholder:text-muted-foreground focus:border-violet-500 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Repository Root
                </label>
                <input
                  type="text"
                  value={repoPath}
                  onChange={(e) => setRepoPath(e.target.value)}
                  className="w-full rounded-md border border-white/[0.1] bg-[#080B14] px-2.5 py-1.5 text-xs text-white focus:border-violet-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Harness Preset
                </label>
                <select
                  value={preset}
                  onChange={(e) => setPreset(e.target.value)}
                  className="w-full rounded-md border border-white/[0.1] bg-[#080B14] px-2.5 py-1.5 text-xs text-white focus:border-violet-500 focus:outline-none"
                >
                  <option value="full">Full (Adaptive + Recovery)</option>
                  <option value="fixed_rag">Fixed-RAG (Top-K)</option>
                  <option value="basic">Basic (No Retrieval)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Provider
                </label>
                <select
                  value={provider}
                  onChange={(e) => {
                    setProvider(e.target.value);
                    if (e.target.value === "deepseek") setModel("deepseek-coder");
                    else if (e.target.value === "openai") setModel("gpt-4o");
                    else if (e.target.value === "anthropic") setModel("claude-3-5-sonnet-20241022");
                    else if (e.target.value === "gemini") setModel("gemini-1.5-pro");
                    else setModel("mock-model");
                  }}
                  className="w-full rounded-md border border-white/[0.1] bg-[#080B14] px-2.5 py-1.5 text-xs text-white focus:border-violet-500 focus:outline-none"
                >
                  <option value="deepseek">DeepSeek</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="gemini">Google Gemini</option>
                  <option value="ollama">Ollama (Local)</option>
                  <option value="mock">Deterministic Mock</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Model
                </label>
                <input
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full rounded-md border border-white/[0.1] bg-[#080B14] px-2.5 py-1.5 text-xs text-white focus:border-violet-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Permission Mode
              </label>
              <select
                value={permissionMode}
                onChange={(e) => setPermissionMode(e.target.value)}
                className="w-full rounded-md border border-white/[0.1] bg-[#080B14] px-2.5 py-1.5 text-xs text-white focus:border-violet-500 focus:outline-none"
              >
                <option value="auto_safe">Auto-Safe (Prompt on Shell, Allow Read/Edit)</option>
                <option value="interactive">Interactive (Prompt All Modifying Actions)</option>
                <option value="read_only">Read-Only (Exploration Only)</option>
                <option value="autonomous">Autonomous (Fully Automated in Container)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={launching}
              className="w-full flex items-center justify-center space-x-2 rounded-md bg-violet-600 px-4 py-2 text-xs font-semibold text-white shadow-sm shadow-violet-600/30 hover:bg-violet-500 transition active:scale-[0.98] disabled:opacity-50"
            >
              {launching ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Initializing Task...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-current" />
                  <span>Start Autonomous Execution</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Recent Sessions Table */}
        <div className="lg:col-span-7 rounded-md border border-white/[0.08] bg-[#0D1220] p-5 flex flex-col">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08] mb-4">
              <div className="flex items-center space-x-2">
                <Clock className="h-4 w-4 text-violet-400" />
                <h2 className="text-sm font-semibold text-white">Recent Sessions</h2>
              </div>
              <span className="text-xs text-muted-foreground font-mono">{sessions.length} total</span>
            </div>

            {loading ? (
              <div className="flex h-48 items-center justify-center text-xs text-muted-foreground font-mono">
                Loading session store...
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/[0.08] text-muted-foreground">
                      <th className="pb-2 font-medium">Session ID and Task</th>
                      <th className="pb-2 font-medium">Status</th>
                      <th className="pb-2 font-medium">Preset</th>
                      <th className="pb-2 font-medium">Tokens / Cost</th>
                      <th className="pb-2 font-medium text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.06]">
                    {sessions.map((s) => (
                      <tr key={s.id} className="hover:bg-white/[0.02] transition">
                        <td className="py-2.5 pr-2">
                          <div className="font-mono font-medium text-white">{s.id}</div>
                          <div className="text-[11px] text-muted-foreground line-clamp-1 max-w-xs">
                            {s.task}
                          </div>
                        </td>
                        <td className="py-2.5">
                          <span
                            className={`inline-flex items-center space-x-1 rounded px-2 py-0.5 text-[10px] font-semibold font-mono ${
                              s.status === "COMPLETED"
                                ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                                : s.status === "RUNNING"
                                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 animate-pulse"
                                : s.status === "PAUSED"
                                ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                                : "bg-red-500/15 text-red-300 border border-red-500/30"
                            }`}
                          >
                            {s.status === "COMPLETED" && <CheckCircle2 className="h-3 w-3" />}
                            {s.status === "RUNNING" && <Loader2 className="h-3 w-3 animate-spin" />}
                            {s.status === "PAUSED" && <PauseCircle className="h-3 w-3" />}
                            {s.status === "FAILED" && <XCircle className="h-3 w-3" />}
                            <span>{s.status}</span>
                          </span>
                        </td>
                        <td className="py-2.5 uppercase font-mono text-[11px] text-muted-foreground">
                          {s.preset}
                        </td>
                        <td className="py-2.5 font-mono text-[11px] text-white">
                          <div>{formatNumber(s.total_tokens)} tok</div>
                          <div className="text-muted-foreground">{formatUSD(s.total_cost_usd)}</div>
                        </td>
                        <td className="py-2.5 text-right">
                          <Link
                            href={`/sessions/${s.id}`}
                            className="inline-flex items-center space-x-1 rounded-md border border-white/[0.1] bg-[#080B14] px-2.5 py-1 text-slate-200 hover:text-white hover:border-violet-500/40 transition"
                          >
                            <span>Inspect</span>
                            <ArrowRight className="h-3 w-3" />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="mt-4 pt-4 border-t border-white/[0.08] flex justify-between items-center text-xs text-muted-foreground font-mono">
            <span>Powered by SQLite persistent SessionStore</span>
            <Link href="/eval" className="text-violet-400 hover:underline font-medium">
              Evaluation Lab →
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
