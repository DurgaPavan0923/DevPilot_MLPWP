"use client";

import React, { useState } from "react";
import {
  Network,
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sparkles,
  GitCommit,
  ArrowRight,
  Maximize2,
} from "lucide-react";

interface Node {
  id: string;
  type: string;
  x: number;
  y: number;
  degree: number;
  pageRank: number;
  summary: string;
}

interface Edge {
  source: string;
  target: string;
  type: string;
}

export function ForceGraph() {
  const [selectedNode, setSelectedNode] = useState<string>("devpilot/agent/runtime.py");
  const [filterQuery, setFilterQuery] = useState("");
  const [zoomLevel, setZoomLevel] = useState(1);

  const nodes: Node[] = [
    { id: "devpilot/agent/runtime.py", type: "module", x: 380, y: 220, degree: 9, pageRank: 0.184, summary: "Core async finite-state machine coordinating analyze, plan, act, observe loop." },
    { id: "devpilot/agent/state.py", type: "module", x: 260, y: 150, degree: 4, pageRank: 0.082, summary: "FSM state definitions and immutable transition dataclasses." },
    { id: "devpilot/agent/recovery.py", type: "module", x: 500, y: 160, degree: 5, pageRank: 0.098, summary: "Bounded error recovery ladder with git snapshot rollback manager." },
    { id: "devpilot/context/hybrid.py", type: "module", x: 380, y: 100, degree: 7, pageRank: 0.142, summary: "Reciprocal Rank Fusion engine combining BM25 and dense embeddings." },
    { id: "devpilot/context/dense.py", type: "module", x: 270, y: 50, degree: 3, pageRank: 0.065, summary: "Dense vector embedding provider client and cosine similarity indexing." },
    { id: "devpilot/context/adaptive_k.py", type: "module", x: 490, y: 50, degree: 4, pageRank: 0.076, summary: "Knee-detection budget curve cutoff to prevent context bloat." },
    { id: "devpilot/safety/sandbox.py", type: "module", x: 200, y: 280, degree: 4, pageRank: 0.088, summary: "Filesystem path jail containment and isolated command execution." },
    { id: "devpilot/safety/command_policy.py", type: "module", x: 120, y: 350, degree: 2, pageRank: 0.045, summary: "Denylist regex filter rejecting dangerous shell metacharacters and fork bombs." },
    { id: "devpilot/verification/runner.py", type: "module", x: 560, y: 280, degree: 3, pageRank: 0.071, summary: "Pre-patch and post-patch pytest validation runner and syntax auditor." },
    { id: "devpilot/session/store.py", type: "module", x: 380, y: 350, degree: 6, pageRank: 0.115, summary: "Persistent atomic SQLite event ledger and telemetry logger." },
    { id: "devpilot/llm/provider.py", type: "adapter", x: 560, y: 380, degree: 3, pageRank: 0.074, summary: "Multi-provider abstraction for DeepSeek, OpenAI, Anthropic, Gemini, Ollama." },
  ];

  const edges: Edge[] = [
    { source: "devpilot/agent/runtime.py", target: "devpilot/agent/state.py", type: "imports" },
    { source: "devpilot/agent/runtime.py", target: "devpilot/agent/recovery.py", type: "imports" },
    { source: "devpilot/agent/runtime.py", target: "devpilot/context/hybrid.py", type: "imports" },
    { source: "devpilot/context/hybrid.py", target: "devpilot/context/dense.py", type: "imports" },
    { source: "devpilot/context/hybrid.py", target: "devpilot/context/adaptive_k.py", type: "imports" },
    { source: "devpilot/agent/runtime.py", target: "devpilot/safety/sandbox.py", type: "imports" },
    { source: "devpilot/safety/sandbox.py", target: "devpilot/safety/command_policy.py", type: "calls" },
    { source: "devpilot/agent/runtime.py", target: "devpilot/verification/runner.py", type: "imports" },
    { source: "devpilot/agent/runtime.py", target: "devpilot/session/store.py", type: "imports" },
    { source: "devpilot/agent/runtime.py", target: "devpilot/llm/provider.py", type: "calls" },
  ];

  const filteredNodes = nodes.filter((n) =>
    n.id.toLowerCase().includes(filterQuery.toLowerCase())
  );

  const selectedNodeObj = nodes.find((n) => n.id === selectedNode) || nodes[0];

  const incomingEdges = edges.filter((e) => e.target === selectedNode);
  const outgoingEdges = edges.filter((e) => e.source === selectedNode);

  const connectedNeighbors = new Set(
    edges
      .filter((e) => e.source === selectedNode || e.target === selectedNode)
      .map((e) => (e.source === selectedNode ? e.target : e.source))
  );

  const handleZoom = (delta: number) => {
    setZoomLevel((prev) => Math.max(0.6, Math.min(1.8, prev + delta)));
  };

  const handleResetZoom = () => {
    setZoomLevel(1);
    setSelectedNode("devpilot/agent/runtime.py");
    setFilterQuery("");
  };

  return (
    <div className="flex flex-col lg:flex-row h-[620px] rounded-md border border-white/[0.08] bg-[#0D1220] overflow-hidden shadow-sm">
      {/* Canvas View */}
      <div className="relative flex-1 bg-[#080B14] p-4 flex flex-col overflow-hidden">
        {/* Top Control Overlay */}
        <div className="absolute top-4 left-4 z-10 flex items-center space-x-2">
          <div className="flex items-center space-x-2 bg-[#0D1220]/90 border border-white/[0.1] rounded-md px-3 py-1.5 shadow-sm backdrop-blur">
            <Search className="h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search AST nodes..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="bg-transparent text-xs font-mono text-white placeholder:text-muted-foreground focus:outline-none w-44"
            />
          </div>

          <div className="flex items-center space-x-1 bg-[#0D1220]/90 border border-white/[0.1] rounded-md p-1 shadow-sm">
            <button
              onClick={() => handleZoom(0.15)}
              title="Zoom In"
              className="h-6 w-6 flex items-center justify-center rounded text-slate-300 hover:text-white hover:bg-white/[0.05]"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => handleZoom(-0.15)}
              title="Zoom Out"
              className="h-6 w-6 flex items-center justify-center rounded text-slate-300 hover:text-white hover:bg-white/[0.05]"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={handleResetZoom}
              title="Reset Layout"
              className="h-6 w-6 flex items-center justify-center rounded text-slate-300 hover:text-white hover:bg-white/[0.05]"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* SVG Graph View */}
        <svg
          className="w-full h-full cursor-crosshair select-none"
          style={{ transform: `scale(${zoomLevel})`, transformOrigin: "center center", transition: "transform 0.15s ease-out" }}
        >
          <defs>
            <pattern id="graph-grid" width="28" height="28" patternUnits="userSpaceOnUse">
              <path d="M 28 0 L 0 0 0 28" fill="none" stroke="rgba(148, 163, 184, 0.05)" strokeWidth="0.5" />
            </pattern>
            <filter id="glow-violet" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="glow" />
              <feComposite in="SourceGraphic" in2="glow" operator="over" />
            </filter>
          </defs>
          <rect width="100%" height="100%" fill="url(#graph-grid)" />

          {/* Directed Edges */}
          {edges.map((e, idx) => {
            const s = nodes.find((n) => n.id === e.source);
            const t = nodes.find((n) => n.id === e.target);
            if (!s || !t) return null;
            const isHighlight =
              selectedNode && (e.source === selectedNode || e.target === selectedNode);

            return (
              <g key={idx}>
                <line
                  x1={s.x}
                  y1={s.y}
                  x2={t.x}
                  y2={t.y}
                  stroke={isHighlight ? "#8b5cf6" : "rgba(148, 163, 184, 0.2)"}
                  strokeWidth={isHighlight ? 2 : 1}
                  strokeDasharray={e.type === "calls" ? "4 2" : undefined}
                />
              </g>
            );
          })}

          {/* Node Circles */}
          {filteredNodes.map((n) => {
            const isSelected = n.id === selectedNode;
            const isNeighbor = connectedNeighbors.has(n.id);
            const nodeRadius = 14 + n.degree * 1.5;

            return (
              <g
                key={n.id}
                onClick={() => setSelectedNode(n.id)}
                className="cursor-pointer transition-transform hover:scale-110"
              >
                {/* Selection Aura */}
                {isSelected && (
                  <circle
                    cx={n.x}
                    cy={n.y}
                    r={nodeRadius + 6}
                    fill="none"
                    stroke="#8b5cf6"
                    strokeWidth={1.5}
                    strokeDasharray="3 3"
                    className="animate-spin-slow origin-center"
                  />
                )}

                <circle
                  cx={n.x}
                  cy={n.y}
                  r={nodeRadius}
                  fill={
                    isSelected
                      ? "#8b5cf6"
                      : isNeighbor
                      ? "#06b6d4"
                      : n.type === "adapter"
                      ? "#f59e0b"
                      : "#1e293b"
                  }
                  stroke={isSelected ? "#ffffff" : isNeighbor ? "#22d3ee" : "rgba(148, 163, 184, 0.4)"}
                  strokeWidth={isSelected ? 2 : 1}
                />

                {/* Node Label */}
                <text
                  x={n.x}
                  y={n.y + nodeRadius + 14}
                  textAnchor="middle"
                  fill={isSelected ? "#ffffff" : "#94a3b8"}
                  fontSize={10}
                  fontFamily="monospace"
                  fontWeight={isSelected ? "bold" : "normal"}
                  className="pointer-events-none select-none"
                >
                  {n.id.split("/").pop()}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Legend */}
        <div className="absolute bottom-3 left-4 flex items-center space-x-3 text-[10px] font-mono text-muted-foreground bg-[#0D1220]/80 border border-white/[0.08] px-2.5 py-1 rounded">
          <span className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-violet-500" />
            <span>Active Target</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-cyan-400" />
            <span>1-Hop Neighbor</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-slate-700" />
            <span>Module</span>
          </span>
        </div>
      </div>

      {/* Right Side: Detailed Node Inspector */}
      <div className="w-full lg:w-80 border-t lg:border-t-0 lg:border-l border-white/[0.08] bg-[#0D1220] p-4 flex flex-col justify-between overflow-y-auto">
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
            <div className="flex items-center space-x-2">
              <Network className="h-4 w-4 text-violet-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-white font-mono">
                Symbol Inspector
              </h4>
            </div>
            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-1.5 py-0.5 rounded">
              PageRank: {selectedNodeObj.pageRank.toFixed(3)}
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div>
              <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                Target Node
              </span>
              <code className="text-xs font-mono font-bold text-white block mt-0.5 break-all">
                {selectedNodeObj.id}
              </code>
            </div>

            <div>
              <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                Node Type
              </span>
              <span className="inline-flex rounded border border-white/[0.1] bg-[#121A2A] px-2 py-0.5 font-mono text-[11px] text-slate-300 mt-0.5">
                {selectedNodeObj.type}
              </span>
            </div>

            <div>
              <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                Summary
              </span>
              <p className="text-xs text-slate-300 leading-relaxed mt-0.5">
                {selectedNodeObj.summary}
              </p>
            </div>
          </div>

          {/* Incoming Imports */}
          <div className="space-y-1.5 pt-2 border-t border-white/[0.06]">
            <span className="text-[10px] uppercase font-mono text-muted-foreground block">
              Incoming References ({incomingEdges.length})
            </span>
            {incomingEdges.length === 0 ? (
              <span className="text-[11px] text-slate-500 font-mono italic">None (Root entry point)</span>
            ) : (
              <ul className="space-y-1 font-mono text-[11px]">
                {incomingEdges.map((e, idx) => (
                  <li
                    key={idx}
                    onClick={() => setSelectedNode(e.source)}
                    className="cursor-pointer text-slate-300 hover:text-cyan-300 flex items-center space-x-1 truncate"
                  >
                    <ArrowRight className="h-3 w-3 text-cyan-400 shrink-0" />
                    <span className="truncate">{e.source.split("/").pop()}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Outgoing Imports */}
          <div className="space-y-1.5 pt-2 border-t border-white/[0.06]">
            <span className="text-[10px] uppercase font-mono text-muted-foreground block">
              Outgoing Imports ({outgoingEdges.length})
            </span>
            {outgoingEdges.length === 0 ? (
              <span className="text-[11px] text-slate-500 font-mono italic">Leaf module</span>
            ) : (
              <ul className="space-y-1 font-mono text-[11px]">
                {outgoingEdges.map((e, idx) => (
                  <li
                    key={idx}
                    onClick={() => setSelectedNode(e.target)}
                    className="cursor-pointer text-slate-300 hover:text-violet-300 flex items-center space-x-1 truncate"
                  >
                    <ArrowRight className="h-3 w-3 text-violet-400 shrink-0" />
                    <span className="truncate">{e.target.split("/").pop()}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="pt-3 border-t border-white/[0.08] text-[10px] font-mono text-muted-foreground text-center">
          NetworkX Directed Graph Engine
        </div>
      </div>
    </div>
  );
}
