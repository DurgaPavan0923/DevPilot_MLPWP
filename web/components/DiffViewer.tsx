"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { Copy, Check, FileCode2 } from "lucide-react";

// Dynamically import Monaco DiffEditor to ensure clean client-side rendering
const DiffEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.DiffEditor),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-96 w-full items-center justify-center bg-slate-950 font-mono text-sm text-slate-500">
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

  const handleCopy = () => {
    navigator.clipboard.writeText(modified);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-slate-950">
      <div className="flex items-center justify-between border-b border-border bg-slate-900 px-4 py-2 text-xs">
        <div className="flex items-center space-x-2">
          <FileCode2 className="h-4 w-4 text-blue-400" />
          <span className="font-mono font-medium text-slate-200">{filename}</span>
          <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400 uppercase">
            {language}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1 rounded bg-slate-800 px-2 py-1 text-slate-300 hover:bg-slate-700 transition"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          <span>{copied ? "Copied" : "Copy Patch"}</span>
        </button>
      </div>

      <div className="h-[520px] w-full">
        <DiffEditor
          height="100%"
          language={language}
          original={original}
          modified={modified}
          theme="vs-dark"
          options={{
            readOnly: true,
            renderSideBySide: true,
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  );
}
