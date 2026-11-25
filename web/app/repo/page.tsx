"use client";

import React, { useState } from "react";
import {
  FolderGit2,
  FileCode,
  Folder,
  FolderOpen,
  ChevronRight,
  ChevronDown,
  Network,
  Copy,
  Check,
  Search,
  Split,
  FileCode2,
  Code2,
} from "lucide-react";
import { ForceGraph } from "@/components/ForceGraph";

interface FileNode {
  name: string;
  path: string;
  type: "file" | "dir";
  status?: "modified" | "clean" | "added";
  children?: FileNode[];
}

const SAMPLE_TREE: FileNode[] = [
  {
    name: "devpilot",
    path: "devpilot",
    type: "dir",
    children: [
      {
        name: "agent",
        path: "devpilot/agent",
        type: "dir",
        children: [
          { name: "runtime.py", path: "devpilot/agent/runtime.py", type: "file", status: "clean" },
          { name: "state.py", path: "devpilot/agent/state.py", type: "file", status: "clean" },
          { name: "events.py", path: "devpilot/agent/events.py", type: "file", status: "clean" },
          { name: "recovery.py", path: "devpilot/agent/recovery.py", type: "file", status: "clean" },
        ],
      },
      {
        name: "context",
        path: "devpilot/context",
        type: "dir",
        children: [
          { name: "hybrid.py", path: "devpilot/context/hybrid.py", type: "file", status: "clean" },
          { name: "dense.py", path: "devpilot/context/dense.py", type: "file", status: "clean" },
          { name: "adaptive_k.py", path: "devpilot/context/adaptive_k.py", type: "file", status: "clean" },
          { name: "fusion.py", path: "devpilot/context/fusion.py", type: "file", status: "clean" },
        ],
      },
      {
        name: "safety",
        path: "devpilot/safety",
        type: "dir",
        children: [
          { name: "sandbox.py", path: "devpilot/safety/sandbox.py", type: "file", status: "clean" },
          { name: "command_policy.py", path: "devpilot/safety/command_policy.py", type: "file", status: "clean" },
          { name: "snapshots.py", path: "devpilot/safety/snapshots.py", type: "file", status: "clean" },
          { name: "redactor.py", path: "devpilot/safety/redactor.py", type: "file", status: "clean" },
        ],
      },
      {
        name: "llm",
        path: "devpilot/llm",
        type: "dir",
        children: [
          { name: "provider.py", path: "devpilot/llm/provider.py", type: "file", status: "clean" },
          { name: "cost_tracker.py", path: "devpilot/llm/cost_tracker.py", type: "file", status: "clean" },
        ],
      },
    ],
  },
  {
    name: "src",
    path: "src",
    type: "dir",
    children: [
      {
        name: "billing",
        path: "src/billing",
        type: "dir",
        children: [
          { name: "calculator.py", path: "src/billing/calculator.py", type: "file", status: "modified" },
        ],
      },
      {
        name: "models",
        path: "src/models",
        type: "dir",
        children: [
          { name: "cart.py", path: "src/models/cart.py", type: "file", status: "clean" },
        ],
      },
    ],
  },
  {
    name: "tests",
    path: "tests",
    type: "dir",
    children: [
      { name: "test_calculator.py", path: "tests/test_calculator.py", type: "file", status: "clean" },
    ],
  },
  { name: "pyproject.toml", path: "pyproject.toml", type: "file", status: "clean" },
  { name: "README.md", path: "README.md", type: "file", status: "clean" },
];

const CODE_SAMPLES: Record<string, string> = {
  "src/billing/calculator.py": `from decimal import Decimal
from src.models.cart import Cart

def compute_order_average(cart: Cart) -> Decimal:
    """Computes the mean price across all items in cart.
    
    Guards against ZeroDivisionError when cart is empty.
    """
    total = sum(i.price for i in cart.items)
    count = len(cart.items)
    if count == 0:
        return Decimal("0.00")
    return total / count
`,
  "devpilot/context/adaptive_k.py": `class AdaptiveKSelector:
    """Detects elbow point on normalized reciprocal-rank score curve."""
    @classmethod
    def select_k(cls, scores: list[float], min_k: int = 1, max_k: int = 15) -> int:
        if not scores:
            return min_k
        # Kneedle algorithm on convex RRF curve
        return max(min_k, min(max_k, int(len(scores) * 0.4)))
`,
  "devpilot/agent/runtime.py": `class AgentRuntime:
    """Asynchronous Finite-State Machine orchestrating tool execution."""
    def __init__(self, provider: LLMProvider, context: HybridRetriever):
        self.provider = provider
        self.context = context
        self.state = AgentState.INIT
        self.history = []
`,
};

export default function RepoExplorerPage() {
  const [activeTab, setActiveTab] = useState<"code" | "graph">("graph");
  const [selectedFile, setSelectedFile] = useState<string>("src/billing/calculator.py");
  const [copiedCode, setCopiedCode] = useState(false);
  const [fileFilter, setFileFilter] = useState("");
  const [openDirs, setOpenDirs] = useState<Record<string, boolean>>({
    devpilot: true,
    "devpilot/agent": true,
    "devpilot/context": true,
    src: true,
    "src/billing": true,
  });

  const toggleDir = (p: string) => {
    setOpenDirs((prev) => ({ ...prev, [p]: !prev[p] }));
  };

  const handleCopyCode = () => {
    const code = CODE_SAMPLES[selectedFile] || "";
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const renderTree = (nodes: FileNode[]) => {
    return (
      <div className="space-y-0.5">
        {nodes.map((node) => {
          if (node.type === "dir") {
            const isOpen = openDirs[node.path] ?? false;
            return (
              <div key={node.path} className="text-xs">
                <div
                  onClick={() => toggleDir(node.path)}
                  className="flex items-center space-x-1.5 py-1 px-2 rounded hover:bg-white/[0.04] cursor-pointer select-none text-slate-300 hover:text-white transition"
                >
                  {isOpen ? (
                    <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                  )}
                  {isOpen ? (
                    <FolderOpen className="h-3.5 w-3.5 text-violet-400" />
                  ) : (
                    <Folder className="h-3.5 w-3.5 text-violet-400" />
                  )}
                  <span className="font-mono">{node.name}</span>
                </div>
                {isOpen && node.children && (
                  <div className="pl-3.5 border-l border-white/[0.06] ml-3">
                    {renderTree(node.children)}
                  </div>
                )}
              </div>
            );
          }

          const isSelected = selectedFile === node.path;
          return (
            <div
              key={node.path}
              onClick={() => {
                setSelectedFile(node.path);
                setActiveTab("code");
              }}
              className={`flex items-center justify-between py-1 px-2 rounded cursor-pointer text-xs transition ${
                isSelected
                  ? "bg-violet-600/20 text-violet-300 font-semibold border border-violet-500/30"
                  : "text-muted-foreground hover:bg-white/[0.03] hover:text-slate-200"
              }`}
            >
              <div className="flex items-center space-x-1.5 truncate">
                <FileCode className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span className="font-mono truncate">{node.name}</span>
              </div>
              {node.status === "modified" && (
                <span className="text-[10px] text-amber-400 font-mono font-bold bg-amber-500/10 px-1 rounded border border-amber-500/30">
                  M
                </span>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  const previewCode =
    CODE_SAMPLES[selectedFile] ||
    `# File: ${selectedFile}\n\n# AST and Symbol definitions extracted via tree-sitter.\n# Real-time indexing completed.`;

  return (
    <div className="space-y-6 pb-12">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-md border border-white/[0.08] bg-[#0D1220] p-4 shadow-sm">
        <div>
          <div className="flex items-center space-x-2">
            <FolderGit2 className="h-5 w-5 text-violet-400" />
            <h1 className="text-base font-bold text-white">Repository Explorer & Call Graph</h1>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Tree-sitter AST symbol extraction, git status indexing, and directed import dependency graph.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setActiveTab("graph")}
            className={`flex items-center space-x-1.5 rounded-md px-3 py-1.5 text-xs font-mono font-medium transition ${
              activeTab === "graph"
                ? "bg-violet-600 text-white font-bold shadow-sm shadow-violet-600/30"
                : "border border-white/[0.1] bg-[#121A2A] text-slate-300 hover:text-white"
            }`}
          >
            <Network className="h-3.5 w-3.5" />
            <span>Dependency Graph</span>
          </button>
          <button
            onClick={() => setActiveTab("code")}
            className={`flex items-center space-x-1.5 rounded-md px-3 py-1.5 text-xs font-mono font-medium transition ${
              activeTab === "code"
                ? "bg-violet-600 text-white font-bold shadow-sm shadow-violet-600/30"
                : "border border-white/[0.1] bg-[#121A2A] text-slate-300 hover:text-white"
            }`}
          >
            <FileCode className="h-3.5 w-3.5" />
            <span>Source Viewer</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Tree + Explorer View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[620px] items-start">
        {/* Left: File Tree */}
        <div className="lg:col-span-4 rounded-md border border-white/[0.08] bg-[#0D1220] p-4 flex flex-col justify-between shadow-sm">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08] mb-3">
              <span className="text-xs font-bold text-white font-mono uppercase tracking-wider">
                Repository Files
              </span>
              <span className="text-[10px] text-muted-foreground font-mono bg-white/[0.04] px-1.5 py-0.5 rounded">
                git:main
              </span>
            </div>
            <div className="overflow-y-auto max-h-[500px]">{renderTree(SAMPLE_TREE)}</div>
          </div>
          <div className="pt-3 border-t border-white/[0.08] text-[11px] text-muted-foreground flex items-center justify-between font-mono">
            <span>Indexed in SQLite</span>
            <span className="text-amber-400 font-medium">1 Modified</span>
          </div>
        </div>

        {/* Right: Code Viewer or Dependency Graph */}
        <div className="lg:col-span-8 rounded-md border border-white/[0.08] bg-[#0D1220] overflow-hidden flex flex-col shadow-sm">
          {activeTab === "graph" ? (
            <ForceGraph />
          ) : (
            <div className="flex flex-col h-[620px] bg-[#0D1220]">
              <div className="flex items-center justify-between border-b border-white/[0.08] bg-[#080B14] px-4 py-2.5 text-xs">
                <div className="flex items-center space-x-2">
                  <FileCode2 className="h-4 w-4 text-violet-400" />
                  <span className="font-mono text-white font-bold">{selectedFile}</span>
                  <span className="rounded border border-white/[0.1] bg-[#121A2A] px-2 py-0.5 text-[10px] text-muted-foreground uppercase font-mono">
                    python
                  </span>
                </div>
                <button
                  onClick={handleCopyCode}
                  className="flex items-center space-x-1 rounded border border-white/[0.1] bg-[#121A2A] px-2.5 py-1 text-xs text-slate-300 hover:text-white transition"
                >
                  {copiedCode ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  <span className="font-mono text-[11px]">{copiedCode ? "Copied" : "Copy"}</span>
                </button>
              </div>
              <pre className="flex-1 p-4 font-mono text-xs text-slate-200 overflow-x-auto leading-relaxed bg-[#080B14]">
                {previewCode}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
