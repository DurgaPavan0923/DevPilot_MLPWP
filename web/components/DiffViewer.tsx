"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { Copy, Check, FileCode2, Split, AlignJustify } from "lucide-react";

// Dynamically import Monaco DiffEditor to ensure clean client-side rendering
const DiffEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.DiffEditor),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-96 w-full items-center justify-center bg-[#0D1220] font-mono text-xs text-muted-foreground">
        Loading Monaco Diff Editor...
      </div>
    ),
  }
);

interface DiffViewerProps {
  original: string;
  modified: string;
  filename?: string;
  language?: string;
}

export function DiffViewer({
  original,
  modified,
  filename = "src/billing/calculator.py",
  language = "python",
}: DiffViewerProps) {
  const [copied, setCopied] = useState(false);
  const [sideBySide, setSideBySide] = useState(true);

  const handleCopy = () => {
    navigator.clipboard.writeText(modified);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-md border border-white/[0.08] bg-[#0D1220]">
      {/* Editor Top Bar */}
      <div className="flex flex-wrap items-center justify-between border-b border-white/[0.08] bg-[#080B14] px-4 py-2.5 text-xs gap-2">
        <div className="flex items-center space-x-2">
          <FileCode2 className="h-4 w-4 text-violet-400" />
          <span className="font-mono font-medium text-white">{filename}</span>
          <span className="rounded border border-white/[0.1] bg-[#121A2A] px-1.5 py-0.5 text-[10px] text-muted-foreground uppercase font-mono">
            {language}
          </span>
          <span className="hidden sm:inline-flex rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-mono text-emerald-400">
            Unified Diff
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {/* Side-by-side vs Inline Toggle */}
          <button
            onClick={() => setSideBySide(!sideBySide)}
            title={sideBySide ? "Switch to inline unified view" : "Switch to side-by-side split view"}
            className="flex items-center space-x-1 rounded-md border border-white/[0.1] bg-[#121A2A] px-2 py-1 text-xs text-slate-300 hover:text-white transition"
          >
            {sideBySide ? <Split className="h-3.5 w-3.5 text-cyan-400" /> : <AlignJustify className="h-3.5 w-3.5 text-violet-400" />}
            <span className="font-mono text-[11px]">{sideBySide ? "Split" : "Inline"}</span>
          </button>

          {/* Copy Patch */}
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1 rounded-md border border-white/[0.1] bg-[#121A2A] px-2.5 py-1 text-xs text-slate-200 hover:text-white hover:border-violet-500/40 transition"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5 text-violet-400" />}
            <span className="font-mono text-[11px]">{copied ? "Copied" : "Copy Patch"}</span>
          </button>
        </div>
      </div>

      {/* Editor Body */}
      <div className="h-[460px] w-full bg-[#080B14]">
        <DiffEditor
          height="100%"
          language={language}
          original={original}
          modified={modified}
          theme="vs-dark"
          options={{
            readOnly: true,
            renderSideBySide: sideBySide,
            minimap: { enabled: false },
            fontSize: 12,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  );
}
