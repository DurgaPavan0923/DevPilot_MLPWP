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
      <div className="flex h-96 w-full items-center justify-center bg-card font-mono text-sm text-muted-foreground">
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
    <div className="flex h-full flex-col overflow-hidden rounded-md border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border bg-muted/40 px-4 py-2 text-xs">
        <div className="flex items-center space-x-2">
          <FileCode2 className="h-4 w-4 text-primary" />
          <span className="font-mono font-medium text-foreground">{filename}</span>
          <span className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground uppercase">
            {language}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1 rounded-md border border-border bg-background px-2.5 py-1 text-xs text-foreground hover:bg-muted transition"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
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
