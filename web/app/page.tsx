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
} from "lucide-react";
import { fetchSessions, createSession } from "@/lib/api";
import { formatUSD, formatNumber } from "@/lib/utils";
import type { MockSession } from "@/lib/mock-data";

export default function HomePage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<MockSession[]>([]);
  const [loading, setLoading] = useState(true);

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

  const components = [
    {
      title: "1. LLM Provider Layer",
      icon: Cpu,
      desc: "Unified async interface across OpenAI, Anthropic, Gemini, DeepSeek, and Ollama. Enforces cost tables, token accounting, rate limiting, and structured tool calling with JSON fallback.",
    },
    {
      title: "2. Repository Context Engine",
      icon: Database,
      desc: "AST symbol indexing via tree-sitter, PageRank-weighted call graphs, hybrid BM25 and dense vector retrieval, with adaptive knee-detection context budgeting.",
    },
    {
      title: "3. Agent Runtime",
      icon: Terminal,
      desc: "Asynchronous finite-state machine with states ANALYZE, PLAN, ACT, OBSERVE, RECOVER, VERIFY, DONE, and FAILED. Supports human-in-the-loop approval gating.",
    },
    {
      title: "4. Tools and Sandbox",
      icon: Layers,
      desc: "Deterministic file reader, patch editor, command executor, and diff generators. Sandboxed inside isolated Docker containers or workspace path jails.",
    },
    {
      title: "5. Bounded Recovery",
      icon: RotateCcw,
      desc: "Automated error classifier mapping syntax, runtime, test, and permission errors to corrective plans with strict retry limits and clean git snapshot rollbacks.",
    },
    {
      title: "6. Verification Engine",
      icon: ShieldCheck,
      desc: "Automated pre-patch and post-patch test execution, syntax validation, regression checks, and clean diff generation to confirm bug resolution.",
    },
    {
      title: "7. Session Store and API",
      icon: Activity,
      desc: "Persistent SQLite event store, FastAPI REST endpoints, and Server-Sent Events (SSE) streaming for real-time trace telemetry and state introspection.",
    },
  ];

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="border-b border-border pb-10">
        <div className="max-w-4xl space-y-4">
          <div className="inline-flex items-center rounded border border-primary/20 bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
            Research Harness for Coding Agents
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            DevPilot
          </h1>
          <p className="text-lg leading-relaxed text-muted-foreground">
            A coding agent harness that retrieves repository context, runs tools in a sandbox, retries on errors with a bounded limit, and verifies changes with tests.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link
              href="/sessions"
              className="inline-flex items-center space-x-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition"
            >
              <Play className="h-4 w-4" />
              <span>Open the demo</span>
            </Link>
            <Link
              href="/docs"
              className="inline-flex items-center space-x-2 rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition"
            >
              <BookOpen className="h-4 w-4 text-muted-foreground" />
              <span>Read the docs</span>
            </Link>
            <Link
              href="/product"
              className="inline-flex items-center space-x-1.5 rounded-md border border-border bg-card px-3.5 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition"
            >
              <span>Architecture</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* The 7 Core Architectural Components */}
      <section className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">7 Modular Components</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Every component sits behind an interface and can be independently swapped, benchmarked, or configured.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {components.map((c, idx) => {
            const Icon = c.icon;
            return (
              <div
                key={idx}
                className="rounded-md border border-border bg-card p-4 space-y-2"
              >
                <div className="flex items-center space-x-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded bg-muted text-primary">
                    <Icon className="h-4 w-4" />
                  </div>
                  <h3 className="text-sm font-semibold text-foreground">{c.title}</h3>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {c.desc}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Operational Metrics Cards (Real Session Store Data) */}
      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-foreground">Session Store Overview</h2>
          <p className="text-xs text-muted-foreground">
            Current activity aggregated from the local SQLite persistent database.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-md border border-border bg-card p-4">
            <span className="text-xs font-medium text-muted-foreground">Recorded Sessions</span>
            <div className="mt-2 text-2xl font-bold font-mono text-foreground">{sessions.length}</div>
            <p className="mt-1 text-[11px] text-muted-foreground">Persisted in SQLite database</p>
          </div>

          <div className="rounded-md border border-border bg-card p-4">
            <span className="text-xs font-medium text-muted-foreground">Active Sessions</span>
            <div className="mt-2 text-2xl font-bold font-mono text-foreground">{activeCount}</div>
            <p className="mt-1 text-[11px] text-muted-foreground">Running agent tasks</p>
          </div>

          <div className="rounded-md border border-border bg-card p-4">
            <span className="text-xs font-medium text-muted-foreground">Completed Tasks</span>
            <div className="mt-2 text-2xl font-bold font-mono text-foreground">{completedCount}</div>
            <p className="mt-1 text-[11px] text-muted-foreground">Verified patch resolutions</p>
          </div>

          <div className="rounded-md border border-border bg-card p-4">
            <span className="text-xs font-medium text-muted-foreground">Tracked Inference Cost</span>
            <div className="mt-2 text-2xl font-bold font-mono text-foreground">{formatUSD(totalCost)}</div>
            <p className="mt-1 text-[11px] text-muted-foreground">Ledger token pricing</p>
          </div>
        </div>
      </section>

      {/* Main Grid: Launcher + Recent Sessions */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Launcher Form */}
        <div className="lg:col-span-5 rounded-md border border-border bg-card p-5 space-y-4">
          <div className="flex items-center space-x-2 pb-3 border-b border-border">
            <Play className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">Launch Agent Task</h2>
          </div>

          <form onSubmit={handleLaunch} className="space-y-3.5">
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                Task Instruction or Bug Report
              </label>
              <textarea
                required
                rows={3}
                value={taskInstruction}
                onChange={(e) => setTaskInstruction(e.target.value)}
                placeholder="e.g. Fix ZeroDivisionError when calculating average order value with empty items..."
                className="w-full rounded-md border border-border bg-background p-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-foreground mb-1">
                  Repository Root
                </label>
                <input
                  type="text"
                  value={repoPath}
                  onChange={(e) => setRepoPath(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground mb-1">
                  Harness Preset
                </label>
                <select
                  value={preset}
                  onChange={(e) => setPreset(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
                >
                  <option value="full">Full (Adaptive + Recovery)</option>
                  <option value="fixed_rag">Fixed-RAG (Top-K)</option>
                  <option value="basic">Basic (No Retrieval)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-foreground mb-1">
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
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
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
                <label className="block text-xs font-medium text-foreground mb-1">
                  Model
                </label>
                <input
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                Permission Mode
              </label>
              <select
                value={permissionMode}
                onChange={(e) => setPermissionMode(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
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
              className="w-full flex items-center justify-center space-x-2 rounded-md bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition disabled:opacity-50"
            >
              {launching ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Initializing Task...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  <span>Start Autonomous Execution</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Recent Sessions Table */}
        <div className="lg:col-span-7 rounded-md border border-border bg-card p-5 flex flex-col">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-border mb-4">
              <div className="flex items-center space-x-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <h2 className="text-sm font-semibold text-foreground">Recent Sessions</h2>
              </div>
              <span className="text-xs text-muted-foreground">{sessions.length} total</span>
            </div>

            {loading ? (
              <div className="flex h-48 items-center justify-center text-xs text-muted-foreground">
                Loading session store...
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground">
                      <th className="pb-2 font-medium">Session ID and Task</th>
                      <th className="pb-2 font-medium">Status</th>
                      <th className="pb-2 font-medium">Preset</th>
                      <th className="pb-2 font-medium">Tokens / Cost</th>
                      <th className="pb-2 font-medium text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {sessions.map((s) => (
                      <tr key={s.id} className="hover:bg-muted/40 transition">
                        <td className="py-2.5 pr-2">
                          <div className="font-mono font-medium text-foreground">{s.id}</div>
                          <div className="text-[11px] text-muted-foreground line-clamp-1 max-w-xs">
                            {s.task}
                          </div>
                        </td>
                        <td className="py-2.5">
                          <span
                            className={`inline-flex items-center space-x-1 rounded px-2 py-0.5 text-[10px] font-semibold ${
                              s.status === "COMPLETED"
                                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30"
                                : s.status === "RUNNING"
                                ? "bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-500/30 animate-pulse"
                                : s.status === "PAUSED"
                                ? "bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30"
                                : "bg-red-500/15 text-red-700 dark:text-red-300 border border-red-500/30"
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
                        <td className="py-2.5 font-mono text-[11px] text-foreground">
                          <div>{formatNumber(s.total_tokens)} tok</div>
                          <div className="text-muted-foreground">{formatUSD(s.total_cost_usd)}</div>
                        </td>
                        <td className="py-2.5 text-right">
                          <Link
                            href={`/sessions/${s.id}`}
                            className="inline-flex items-center space-x-1 rounded-md border border-border bg-background px-2.5 py-1 text-foreground hover:bg-muted transition"
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

          <div className="mt-4 pt-4 border-t border-border flex justify-between items-center text-xs text-muted-foreground">
            <span>Powered by SQLite persistent SessionStore</span>
            <Link href="/eval" className="text-primary hover:underline">
              Evaluation Lab →
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
