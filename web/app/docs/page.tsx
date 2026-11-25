"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Terminal,
  Server,
  Key,
  Shield,
  Layers,
  FileCode2,
  BookOpen,
  Search,
  Copy,
  Check,
  Cpu,
  Database,
  RotateCcw,
  ShieldCheck,
  ChevronRight,
  ExternalLink,
} from "lucide-react";

export default function DocsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(id);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const cliCommands = [
    {
      id: "cli-run",
      command: "devpilot run --task <text> [options]",
      description: "Executes an autonomous coding task on the current or specified repository.",
      options: [
        "--task, -t TEXT: Task instruction or issue description [required]",
        "--repo, -r PATH: Target repository path (default: .)",
        "--preset [full|fixed_rag|basic]: Harness preset configuration (default: full)",
        "--provider TEXT: LLM provider name (default: deepseek)",
        "--model TEXT: Model identifier (default: deepseek-coder)",
        "--mode [auto_safe|interactive|read_only|autonomous]: Safety permission mode (default: auto_safe)",
        "--max-steps INT: Maximum allowed agent steps (default: 30)",
        "--timeout INT: Session timeout in seconds (default: 600)",
      ],
    },
    {
      id: "cli-serve",
      command: "devpilot serve [options]",
      description: "Launches the FastAPI backend server and WebSocket/SSE streaming server.",
      options: [
        "--host TEXT: Bind network interface (default: 0.0.0.0)",
        "--port INT: Port number (default: 8000)",
        "--reload: Enable automatic code reload for local development",
      ],
    },
    {
      id: "cli-eval",
      command: "devpilot eval run [options]",
      description: "Runs the comparative evaluation suite across the three harness presets.",
      options: [
        "--suite PATH: Path to benchmark task suite JSON (default: builtin-sample)",
        "--preset [full|fixed_rag|basic]: Preset to evaluate (can specify multiple)",
        "--seeds TEXT: Comma-separated seeds for multi-seed verification (default: 42,137,2026)",
        "--concurrency INT: Concurrent task workers (default: 4)",
        "--results-dir PATH: Destination directory for evaluation reports (default: results)",
      ],
    },
    {
      id: "cli-index",
      command: "devpilot index build [options]",
      description: "Builds and caches the AST symbol index and call graph for a repository.",
      options: [
        "--repo PATH: Repository root directory (default: .)",
        "--output PATH: Cache index file path",
      ],
    },
  ];

  const apiEndpoints = [
    { method: "GET", path: "/api/health", desc: "System health check, version, and registered LLM providers." },
    { method: "GET", path: "/api/sessions", desc: "List all persisted sessions with step, status, and token summaries." },
    { method: "POST", path: "/api/sessions", desc: "Create and initialize an autonomous coding session." },
    { method: "GET", path: "/api/sessions/{id}", desc: "Retrieve session metadata, current state, and configuration." },
    { method: "GET", path: "/api/sessions/{id}/diff", desc: "Retrieve original vs modified unified patch diff." },
    { method: "GET", path: "/api/sessions/{id}/events", desc: "Server-Sent Events (SSE) real-time event stream." },
    { method: "POST", path: "/api/sessions/{id}/approval", desc: "Post human-in-the-loop decision (approve/reject)." },
    { method: "GET", path: "/api/eval/runs", desc: "List historical comparative benchmark runs." },
    { method: "GET", path: "/api/eval/latest", desc: "Fetch the most recent evaluation report JSON." },
    { method: "GET", path: "/api/repo/tree", desc: "Read workspace directory tree and file status." },
    { method: "GET", path: "/api/repo/file", desc: "Read file contents for syntax highlighting." },
    { method: "GET", path: "/api/repo/graph", desc: "Export NetworkX AST dependency graph as node-link JSON." },
  ];

  const envVars = [
    { name: "DEVPILOT_PROVIDER", required: "No", default: "deepseek", desc: "Default LLM provider (deepseek, openai, anthropic, gemini, ollama)." },
    { name: "DEVPILOT_MODEL", required: "No", default: "deepseek-coder", desc: "Default model name used for generation and tool planning." },
    { name: "DEVPILOT_DB_PATH", required: "No", default: "devpilot_sessions.db", desc: "SQLite database file path for session and event persistence." },
    { name: "DEVPILOT_SANDBOX_MODE", required: "No", default: "jail", desc: "Execution isolation mode: jail (path check) or docker (container)." },
    { name: "DEVPILOT_MAX_RETRIES", required: "No", default: "3", desc: "Ceiling for bounded error recovery before initiating snapshot rollback." },
    { name: "NEXT_PUBLIC_API_URL", required: "No", default: "http://localhost:8000", desc: "FastAPI backend endpoint for the Next.js frontend." },
  ];

  const filteredCommands = cliCommands.filter((c) =>
    c.command.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredEndpoints = apiEndpoints.filter((e) =>
    e.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
    e.desc.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-12 pb-16">
      {/* Header */}
      <div className="border-b border-white/[0.08] pb-6 max-w-4xl space-y-3">
        <div className="inline-flex items-center space-x-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs font-mono font-medium text-violet-300">
          <BookOpen className="h-3.5 w-3.5" />
          <span>TECHNICAL MANUAL & SPECIFICATION</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
          Documentation & API Reference
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Complete CLI reference, REST endpoint schemas, environment configuration, and sandboxing architecture for the DevPilot autonomous coding agent harness.
        </p>

        {/* In-page Search */}
        <div className="pt-2 max-w-md">
          <div className="relative">
            <Search className="h-4 w-4 absolute left-3 top-2.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search CLI commands, REST endpoints..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-md bg-[#0D1220] border border-white/[0.1] pl-9 pr-3 py-2 text-xs font-mono text-white placeholder:text-muted-foreground focus:outline-none focus:border-violet-500"
            />
          </div>
        </div>
      </div>

      {/* Quick Navigation Sections */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        <a
          href="#quickstart"
          className="p-3 rounded-md border border-white/[0.08] bg-[#0D1220] hover:border-violet-500/40 text-slate-300 hover:text-white transition"
        >
          <span className="text-violet-400 block mb-1">01.</span>
          <span className="font-bold">Quickstart & Setup</span>
        </a>
        <a
          href="#cli"
          className="p-3 rounded-md border border-white/[0.08] bg-[#0D1220] hover:border-violet-500/40 text-slate-300 hover:text-white transition"
        >
          <span className="text-violet-400 block mb-1">02.</span>
          <span className="font-bold">CLI Reference</span>
        </a>
        <a
          href="#api"
          className="p-3 rounded-md border border-white/[0.08] bg-[#0D1220] hover:border-violet-500/40 text-slate-300 hover:text-white transition"
        >
          <span className="text-violet-400 block mb-1">03.</span>
          <span className="font-bold">REST API Schema</span>
        </a>
        <a
          href="#security"
          className="p-3 rounded-md border border-white/[0.08] bg-[#0D1220] hover:border-violet-500/40 text-slate-300 hover:text-white transition"
        >
          <span className="text-violet-400 block mb-1">04.</span>
          <span className="font-bold">Security & Jail</span>
        </a>
      </div>

      {/* Quickstart Section */}
      <section id="quickstart" className="space-y-4">
        <div className="flex items-center space-x-2">
          <Terminal className="h-5 w-5 text-violet-400" />
          <h2 className="text-lg font-bold text-white">Installation & Quickstart</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          DevPilot runs on Python 3.11+ and ships both an autonomous CLI tool and an interactive FastAPI + Next.js web application.
        </p>

        <div className="space-y-3 font-mono text-xs">
          <div className="rounded-md border border-white/[0.08] bg-[#0D1220] p-4 space-y-2">
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>1. Clone and Install Dependencies</span>
              <button
                onClick={() => handleCopy("install", "git clone https://github.com/DurgaPavan0923/DevPilot_MLPWP.git\ncd DevPilot_MLPWP\npip install -e \".[dev,full]\"")}
                className="hover:text-white flex items-center space-x-1"
              >
                {copiedIndex === "install" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                <span>{copiedIndex === "install" ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <pre className="bg-[#080B14] p-3 rounded text-slate-300 overflow-x-auto">
              git clone https://github.com/DurgaPavan0923/DevPilot_MLPWP.git{"\n"}
              cd DevPilot_MLPWP{"\n"}
              pip install -e &quot;.[dev,full]&quot;
            </pre>
          </div>

          <div className="rounded-md border border-white/[0.08] bg-[#0D1220] p-4 space-y-2">
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>2. Launch the Web UI & API Server</span>
              <button
                onClick={() => handleCopy("serve", "# Terminal 1: Launch FastAPI Backend\ndevpilot serve --port 8000\n\n# Terminal 2: Launch Next.js Dashboard\ncd web && pnpm dev")}
                className="hover:text-white flex items-center space-x-1"
              >
                {copiedIndex === "serve" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                <span>{copiedIndex === "serve" ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <pre className="bg-[#080B14] p-3 rounded text-slate-300 overflow-x-auto">
              # Terminal 1: Launch FastAPI Backend{"\n"}
              devpilot serve --port 8000{"\n\n"}
              # Terminal 2: Launch Next.js Dashboard{"\n"}
              cd web &amp;&amp; pnpm dev
            </pre>
          </div>
        </div>
      </section>

      {/* CLI Reference */}
      <section id="cli" className="space-y-4">
        <div className="flex items-center space-x-2">
          <Terminal className="h-5 w-5 text-violet-400" />
          <h2 className="text-lg font-bold text-white">CLI Command Reference</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          The DevPilot CLI is powered by Typer and provides commands for autonomous execution, evaluation, indexing, and serving.
        </p>

        <div className="space-y-4">
          {filteredCommands.map((cmd) => (
            <div key={cmd.id} className="rounded-md border border-white/[0.08] bg-[#0D1220] p-4 space-y-2 shadow-sm">
              <div className="flex items-center justify-between">
                <code className="text-xs font-mono font-bold text-cyan-300 bg-[#080B14] px-2.5 py-1 rounded border border-white/[0.06] block">
                  {cmd.command}
                </code>
                <button
                  onClick={() => handleCopy(cmd.id, cmd.command)}
                  className="text-muted-foreground hover:text-white text-xs flex items-center space-x-1 font-mono"
                >
                  {copiedIndex === cmd.id ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  <span>{copiedIndex === cmd.id ? "Copied" : "Copy"}</span>
                </button>
              </div>
              <p className="text-xs text-slate-300">{cmd.description}</p>
              <div className="pt-2 border-t border-white/[0.06] space-y-1">
                <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-wider">
                  Options:
                </span>
                <ul className="text-xs font-mono text-muted-foreground space-y-1">
                  {cmd.options.map((opt, oIdx) => (
                    <li key={oIdx} className="pl-2 border-l border-white/[0.1] text-[11px] text-slate-400">
                      {opt}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* REST API Reference */}
      <section id="api" className="space-y-4">
        <div className="flex items-center space-x-2">
          <Server className="h-5 w-5 text-violet-400" />
          <h2 className="text-lg font-bold text-white">REST API Reference</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          The FastAPI backend exposes endpoints for session management, real-time event streaming, and repository inspection.
        </p>

        <div className="rounded-md border border-white/[0.08] bg-[#0D1220] overflow-x-auto shadow-sm">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] bg-[#080B14] text-muted-foreground font-mono">
                <th className="p-3 font-semibold">Method</th>
                <th className="p-3 font-semibold">Endpoint</th>
                <th className="p-3 font-semibold">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06]">
              {filteredEndpoints.map((ep, idx) => (
                <tr key={idx} className="hover:bg-white/[0.02] transition">
                  <td className="p-3 font-mono font-bold">
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-mono ${
                        ep.method === "GET"
                          ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
                          : "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                      }`}
                    >
                      {ep.method}
                    </span>
                  </td>
                  <td className="p-3 font-mono text-white font-medium">{ep.path}</td>
                  <td className="p-3 text-slate-300">{ep.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Environment Configuration */}
      <section className="space-y-4">
        <div className="flex items-center space-x-2">
          <Key className="h-5 w-5 text-violet-400" />
          <h2 className="text-lg font-bold text-white">Environment Configuration</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Configure API credentials, workspace locations, and persistence parameters via environment variables or a .env file.
        </p>

        <div className="rounded-md border border-white/[0.08] bg-[#0D1220] overflow-x-auto shadow-sm">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] bg-[#080B14] text-muted-foreground font-mono">
                <th className="p-3 font-semibold">Variable</th>
                <th className="p-3 font-semibold">Required</th>
                <th className="p-3 font-semibold">Default</th>
                <th className="p-3 font-semibold">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06] font-mono text-[11px]">
              {envVars.map((v, idx) => (
                <tr key={idx} className="hover:bg-white/[0.02]">
                  <td className="p-3 font-bold text-white">{v.name}</td>
                  <td className="p-3 text-muted-foreground">{v.required}</td>
                  <td className="p-3 text-cyan-400">{v.default}</td>
                  <td className="p-3 font-sans text-xs text-slate-300">{v.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Security and Sandboxing */}
      <section id="security" className="space-y-4">
        <div className="flex items-center space-x-2">
          <Shield className="h-5 w-5 text-violet-400" />
          <h2 className="text-lg font-bold text-white">Security & Sandboxing Architecture</h2>
        </div>
        <div className="rounded-md border border-white/[0.08] bg-[#0D1220] p-6 space-y-3 text-xs text-slate-300 leading-relaxed shadow-sm">
          <p>
            DevPilot enforces multiple defensive layers to ensure autonomous agent actions cannot escape workspace boundaries or execute unauthorized destructive commands:
          </p>
          <ul className="list-disc pl-5 space-y-2 text-slate-200">
            <li>
              <strong className="text-white">Workspace Path Jail:</strong> All file reading, editing, and diffing tools canonicalize targets with realpath and enforce containment within the repository root. Backslash traversals (e.g. on Windows) and symlink dereference attacks are strictly blocked.
            </li>
            <li>
              <strong className="text-white">Hermetic Docker Isolation:</strong> In Docker mode, shell commands execute within a sandboxed container with dropped capabilities, non-root UID execution, memory caps, and egress network denial.
            </li>
            <li>
              <strong className="text-white">Denylist Command Filtering:</strong> Dangerous shell primitives, fork bombs, recursive file deletions, and disk modifications outside the workspace are blocked before shell invocation.
            </li>
            <li>
              <strong className="text-white">Bounded Recovery:</strong> Error classifiers detect repeated failures and trigger clean git baseline snapshot rollbacks when the 3-attempt ceiling is reached.
            </li>
          </ul>
        </div>
      </section>
    </div>
  );
}
