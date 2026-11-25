"use client";

import React, { useState } from "react";
import { Network, Search } from "lucide-react";

interface Node {
  id: string;
  type: string;
  x: number;
  y: number;
  degree: number;
}

interface Edge {
  source: string;
  target: string;
  type: string;
}

export function ForceGraph() {
  const [selectedNode, setSelectedNode] = useState<string | null>("devpilot/agent/runtime.py");
  const [filterQuery, setFilterQuery] = useState("");

  const nodes: Node[] = [
    { id: "devpilot/agent/runtime.py", type: "module", x: 380, y: 220, degree: 9 },
    { id: "devpilot/agent/state.py", type: "module", x: 260, y: 150, degree: 4 },
    { id: "devpilot/recovery/policy.py", type: "module", x: 500, y: 160, degree: 5 },
    { id: "devpilot/context/hybrid.py", type: "module", x: 380, y: 100, degree: 7 },
    { id: "devpilot/context/dense.py", type: "module", x: 270, y: 50, degree: 3 },
    { id: "devpilot/context/adaptive_k.py", type: "module", x: 490, y: 50, degree: 4 },
    { id: "devpilot/safety/sandbox.py", type: "module", x: 200, y: 280, degree: 4 },
    { id: "devpilot/safety/command_policy.py", type: "module", x: 120, y: 350, degree: 2 },
    { id: "devpilot/verify/runner.py", type: "module", x: 560, y: 280, degree: 3 },
    { id: "devpilot/session/store.py", type: "module", x: 380, y: 350, degree: 6 },
    { id: "devpilot/llm/adapters/deepseek.py", type: "adapter", x: 560, y: 380, degree: 3 },
  ];

  const edges: Edge[] = [
    { source: "devpilot/agent/runtime.py", target: "devpilot/agent/state.py", type: "imports" },
    { source: "devpilot/agent/runtime.py", target: "devpilot/recovery/policy.py", type: "imports" },
    { source: "devpilot/agent/runtime.py", target: "devpilot/context/hybrid.py", type: "imports" },
    { source: "devpilot/context/hybrid.py", target: "devpilot/context/dense.py", type: "imports" },
    { source: "devpilot/context/hybrid.py", target: "devpilot/context/adaptive_k.py", type: "imports" },
    { source: "devpilot/agent/runtime.py", target: "devpilot/safety/sandbox.py", type: "imports" },
    { source: "devpilot/safety/sandbox.py", target: "devpilot/safety/command_policy.py", type: "calls" },
    { source: "devpilot/agent/runtime.py", target: "devpilot/verify/runner.py", type: "imports" },
    { source: "devpilot/agent/runtime.py", target: "devpilot/session/store.py", type: "imports" },
  ];

  const filteredNodes = nodes.filter((n) =>
    n.id.toLowerCase().includes(filterQuery.toLowerCase())
  );

  const selectedNodeObj = nodes.find((n) => n.id === selectedNode);
  const connectedNeighbors = new Set(
    edges
      .filter((e) => e.source === selectedNode || e.target === selectedNode)
      .map((e) => (e.source === selectedNode ? e.target : e.source))
  );

  return (
    <div className="flex flex-col lg:flex-row h-[620px] rounded-md border border-border bg-card overflow-hidden">
      {/* Canvas View */}
      <div className="relative flex-1 bg-muted/10 p-4 flex flex-col">
        <div className="absolute top-4 left-4 z-10 flex items-center space-x-2 bg-card/90 border border-border rounded-md px-3 py-1.5 shadow-sm">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Filter nodes..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            className="bg-transparent text-xs text-foreground placeholder:text-muted-foreground focus:outline-none w-48"
          />
        </div>

        <svg className="w-full h-full cursor-crosshair">
          <defs>
            <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
              <path d="M 30 0 L 0 0 0 30" fill="none" stroke="currentColor" className="text-border/40" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Edges */}
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
                  stroke={isHighlight ? "#0f766e" : "#94a3b8"}
                  strokeWidth={isHighlight ? 2.5 : 1}
                  strokeDasharray={e.type === "calls" ? "4,4" : undefined}
                />
              </g>
            );
          })}

          {/* Nodes */}
          {filteredNodes.map((node) => {
            const isSelected = selectedNode === node.id;
            const isNeighbor = connectedNeighbors.has(node.id);

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onClick={() => setSelectedNode(node.id)}
                className="cursor-pointer transition-transform hover:scale-110"
              >
                <circle
                  r={isSelected ? 18 : 12}
                  fill={
                    isSelected
                      ? "#0f766e"
                      : isNeighbor
                      ? "#10b981"
                      : node.type === "adapter"
                      ? "#0369a1"
                      : "#64748b"
                  }
                  stroke={isSelected ? "#14b8a6" : "#cbd5e1"}
                  strokeWidth={isSelected ? 3 : 1.5}
                />
                <text
                  y={isSelected ? 28 : 22}
                  textAnchor="middle"
                  className="font-mono text-[10px] fill-foreground font-medium select-none pointer-events-none"
                >
                  {node.id.split("/").pop()}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Node Inspector Panel */}
      <div className="w-full lg:w-80 border-t lg:border-t-0 lg:border-l border-border bg-card p-4 flex flex-col justify-between">
        <div>
          <div className="flex items-center space-x-2 pb-3 border-b border-border">
            <Network className="h-4 w-4 text-primary" />
            <h3 className="font-semibold text-sm text-foreground">Dependency Inspector</h3>
          </div>

          {selectedNodeObj ? (
            <div className="mt-4 space-y-4">
              <div>
                <span className="text-[11px] font-mono text-muted-foreground uppercase">Selected Node</span>
                <p className="font-mono text-xs text-foreground font-bold break-all mt-0.5">
                  {selectedNodeObj.id}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-md border border-border bg-muted/40 p-2">
                  <span className="text-muted-foreground text-[10px] block">Node Type</span>
                  <span className="font-semibold text-foreground capitalize">
                    {selectedNodeObj.type}
                  </span>
                </div>
                <div className="rounded-md border border-border bg-muted/40 p-2">
                  <span className="text-muted-foreground text-[10px] block">Degree (In/Out)</span>
                  <span className="font-semibold text-primary">{selectedNodeObj.degree}</span>
                </div>
              </div>

              <div>
                <span className="text-[11px] font-mono text-muted-foreground uppercase">
                  Connected Dependents ({connectedNeighbors.size})
                </span>
                <div className="mt-1 space-y-1 max-h-48 overflow-y-auto">
                  {Array.from(connectedNeighbors).map((nbr) => (
                    <div
                      key={nbr}
                      onClick={() => setSelectedNode(nbr)}
                      className="cursor-pointer rounded-md bg-muted/40 px-2 py-1 text-xs font-mono text-muted-foreground hover:bg-muted hover:text-foreground transition"
                    >
                      {nbr}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="mt-6 text-xs text-muted-foreground">Click a node on the canvas to inspect its dependency relationships.</p>
          )}
        </div>

        <div className="pt-3 border-t border-border text-[11px] text-muted-foreground">
          Tree-sitter AST and Graph expansion engine
        </div>
      </div>
    </div>
  );
}
