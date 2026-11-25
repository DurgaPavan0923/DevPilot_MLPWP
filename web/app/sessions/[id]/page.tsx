"use client";

import React, { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Play,
  Pause,
  Square,
  RotateCcw,
  Terminal,
  FileCode2,
  Database,
  Coins,
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  Copy,
  Check,
  Cpu,
  Layers,
  Sparkles,
  Lock,
  GitCommit,
  Split,
  Eye,
} from "lucide-react";
import { Stepper, type FSMState } from "@/components/Stepper";
import { DiffViewer } from "@/components/DiffViewer";
import {
  MOCK_SESSIONS,
  MOCK_EVENT_STREAM,
  MOCK_DIFF_ORIGINAL,
  MOCK_DIFF_MODIFIED,
  MOCK_RETRIEVED_CHUNKS,
  type MockAgentEvent,
} from "@/lib/mock-data";
import { fetchSessionDiff } from "@/lib/api";
import { formatUSD, formatNumber } from "@/lib/utils";

export default function LiveSessionPage() {
  const params = useParams();
  const sessionId = (params?.id as string) || "sess_demo_alpha_92";
  const sessionMeta = MOCK_SESSIONS.find((s) => s.id === sessionId);
  const taskTitle = sessionMeta?.task || "Fix ZeroDivisionError when calculating average order value with empty cart items";

  // Event stream state
  const [events, setEvents] = useState<MockAgentEvent[]>([]);
  const [eventFilter, setEventFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [fsmState, setFsmState] = useState<FSMState>("ANALYZE");
  const [recoveriesCount, setRecoveriesCount] = useState(0);
  const [sessionStatus, setSessionStatus] = useState<string>("RUNNING");
  const [autoScroll, setAutoScroll] = useState(true);
  const [activeTab, setActiveTab] = useState<"events" | "context" | "tools" | "cost">("events");

  // Diff state
  const [diffOriginal, setDiffOriginal] = useState(MOCK_DIFF_ORIGINAL);
  const [diffModified, setDiffModified] = useState(MOCK_DIFF_MODIFIED);
  const [activeDiffFile, setActiveDiffFile] = useState("src/billing/calculator.py");

  // Approval state
  const [approvalPending, setApprovalPending] = useState(false);
  const [copiedId, setCopiedId] = useState(false);

  // Expanded tool calls accordion
  const [expandedCalls, setExpandedCalls] = useState<Record<string, boolean>>({});

  const feedEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setEvents(MOCK_EVENT_STREAM);
    if (sessionMeta) {
      setSessionStatus(sessionMeta.status);
      if (sessionMeta.status === "COMPLETED") {
        setFsmState("DONE");
        setRecoveriesCount(0);
      } else if (sessionMeta.status === "FAILED") {
        setFsmState("FAILED");
        setRecoveriesCount(3);
      } else if (sessionMeta.status === "RUNNING") {
        setFsmState("ACT");
        setRecoveriesCount(1);
      } else if (sessionMeta.status === "PAUSED") {
        setFsmState("PLAN");
        setRecoveriesCount(0);
      }
    } else {
      setFsmState("DONE");
      setSessionStatus("COMPLETED");
    }

    fetchSessionDiff(sessionId).then((d) => {
      setDiffOriginal(d.original);
      setDiffModified(d.modified);
    });
  }, [sessionId, sessionMeta]);

  useEffect(() => {
    if (autoScroll) {
      feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [events, autoScroll]);

  const toggleAccordion = (id: string) => {
    setExpandedCalls((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleCopyId = () => {
    navigator.clipboard.writeText(sessionId);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const filteredEvents = events.filter((e) => {
    if (eventFilter === "THOUGHTS" && e.type !== "THOUGHT") return false;
    if (eventFilter === "TOOLS" && e.type !== "TOOL_CALL" && e.type !== "TOOL_RESULT") return false;
    if (eventFilter === "RECOVERY" && e.type !== "RECOVERY") return false;
    if (eventFilter === "STATE" && e.type !== "STATE_CHANGE") return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const stringified = JSON.stringify(e).toLowerCase();
      return stringified.includes(q);
    }
    return true;
  });

  // Dynamic token accounting derived directly from event stream or mock metadata
  const streamPromptTokens = events.reduce((sum, evt) => {
    if (evt.type === "THOUGHT" && evt.data.thought) {
      return sum + Math.round(evt.data.thought.length / 3.5);
    }
    return sum;
  }, 1280);

  const streamCompletionTokens = events.reduce((sum, evt) => {
    if (evt.type === "TOOL_RESULT" && evt.data.output) {
      return sum + Math.round(evt.data.output.length / 4.0);
    }
    return sum;
  }, 412);

  const totalTokens = sessionMeta ? sessionMeta.total_tokens : streamPromptTokens + streamCompletionTokens;
  const promptTokens = sessionMeta ? Math.round(sessionMeta.total_tokens * 0.75) : streamPromptTokens;
  const completionTokens = sessionMeta ? sessionMeta.total_tokens - promptTokens : streamCompletionTokens;
  const totalCostUSD = sessionMeta ? sessionMeta.total_cost_usd : (promptTokens * 0.14 + completionTokens * 0.28) / 1_000_000;

  const handlePause = async () => {
    setSessionStatus("PAUSED");
    setFsmState("PLAN");
  };

  const handleResume = async () => {
    setSessionStatus("RUNNING");
    setFsmState("ACT");
  };

  const handleStop = async () => {
    setSessionStatus("STOPPED");
    setFsmState("FAILED");
  };

  const handleRollback = async () => {
    alert("Rolled back workspace changes to clean baseline snapshot.");
    setDiffModified(diffOriginal);
  };

  const handleApproval = (decision: boolean) => {
    setApprovalPending(false);
    alert(`Human decision registered: ${decision ? "APPROVED" : "REJECTED"}`);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Demo Notice Banner */}
      <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 flex items-start space-x-3 text-xs">
        <span className="rounded bg-amber-500/20 px-2 py-0.5 font-mono text-[10px] font-semibold text-amber-300 uppercase tracking-wider shrink-0 mt-0.5">
          DEMO DATA
        </span>
        <div className="text-slate-300 leading-relaxed text-[11px]">
          <span className="font-semibold text-white">Interactive Session Command Center:</span> Displaying recorded telemetry, AST retrieval scores, and verified diff inspections. To execute autonomous runs on your live codebase, connect the FastAPI backend with <code className="text-amber-300 bg-amber-500/20 px-1 rounded font-mono">devpilot serve</code>.
        </div>
      </div>

      {/* Session Top Bar: ID, Status, and Global Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 rounded-md border border-white/[0.08] bg-[#0D1220] p-4 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <span className="font-mono text-base font-bold text-white tracking-tight">{sessionId}</span>
            <button
              onClick={handleCopyId}
              title="Copy Session ID"
              className="flex h-6 w-6 items-center justify-center rounded border border-white/[0.08] bg-[#121A2A] text-muted-foreground hover:text-white transition"
            >
              {copiedId ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
            </button>
            <span
              className={`rounded px-2.5 py-0.5 text-[11px] font-mono font-bold uppercase tracking-wider ${
                sessionStatus === "COMPLETED"
                  ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                  : sessionStatus === "RUNNING"
                  ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 animate-pulse"
                  : sessionStatus === "PAUSED"
                  ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                  : "bg-red-500/15 text-red-300 border border-red-500/30"
              }`}
            >
              {sessionStatus}
            </span>
          </div>
          <p className="text-xs text-slate-300 font-medium line-clamp-1 max-w-2xl">
            {taskTitle}
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2">
          {sessionStatus === "RUNNING" ? (
            <button
              onClick={handlePause}
              className="flex items-center space-x-1.5 rounded-md border border-white/[0.1] bg-[#121A2A] px-3 py-1.5 text-xs font-medium text-slate-200 hover:text-white hover:border-violet-500/40 transition"
            >
              <Pause className="h-3.5 w-3.5 text-amber-400" />
              <span>Pause</span>
            </button>
          ) : (
            <button
              onClick={handleResume}
              className="flex items-center space-x-1.5 rounded-md border border-white/[0.1] bg-[#121A2A] px-3 py-1.5 text-xs font-medium text-slate-200 hover:text-white hover:border-violet-500/40 transition"
            >
              <Play className="h-3.5 w-3.5 text-emerald-400 fill-current" />
              <span>Resume</span>
            </button>
          )}

          <button
            onClick={handleStop}
            className="flex items-center space-x-1.5 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/20 transition"
          >
            <Square className="h-3.5 w-3.5 fill-current" />
            <span>Stop</span>
          </button>

          <button
            onClick={handleRollback}
            className="flex items-center space-x-1.5 rounded-md border border-white/[0.1] bg-[#121A2A] px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white transition"
          >
            <RotateCcw className="h-3.5 w-3.5 text-cyan-400" />
            <span>Rollback Baseline</span>
          </button>
        </div>
      </div>

      {/* Human-in-the-Loop Approval Alert Banner (when requested) */}
      {approvalPending && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-md border border-amber-500/40 bg-amber-500/10 p-4">
          <div className="flex items-start space-x-3">
            <ShieldAlert className="h-5 w-5 text-amber-400 mt-0.5 shrink-0" />
            <div>
              <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Human-in-the-Loop Approval Required
              </h4>
              <p className="text-xs text-slate-300 mt-0.5">
                The agent is requesting permission to execute shell command:{" "}
                <code className="rounded bg-[#080B14] border border-white/[0.08] px-1.5 py-0.5 font-mono text-cyan-300 text-[11px]">
                  pytest tests/test_calculator.py
                </code>
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleApproval(false)}
              className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-400 hover:bg-red-500/20 transition"
            >
              Reject Action
            </button>
            <button
              onClick={() => handleApproval(true)}
              className="rounded-md bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-500 transition"
            >
              Approve Execution
            </button>
          </div>
        </div>
      )}

      {/* Three-Panel Command Center Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Panel: Execution Overview (col-span-3) */}
        <div className="lg:col-span-3 rounded-md border border-white/[0.08] bg-[#0D1220] p-4 space-y-4 shadow-sm">
          <div className="flex items-center space-x-2 pb-3 border-b border-white/[0.08]">
            <Cpu className="h-4 w-4 text-violet-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-white font-mono">
              Execution Specs
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                Target Repository
              </span>
              <span className="font-mono text-slate-200 mt-0.5 block truncate">
                ./src/billing
              </span>
            </div>

            <div>
              <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                Harness Preset
              </span>
              <span className="inline-flex items-center rounded border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 font-mono text-[11px] font-semibold text-violet-300 mt-0.5 uppercase">
                {sessionMeta?.preset || "full"}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/[0.06]">
              <div>
                <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                  Provider
                </span>
                <span className="font-mono text-slate-200 text-[11px] capitalize">
                  {sessionMeta?.provider || "deepseek"}
                </span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                  Model
                </span>
                <span className="font-mono text-slate-200 text-[11px] truncate block">
                  {sessionMeta?.model || "deepseek-coder"}
                </span>
              </div>
            </div>

            <div className="pt-2 border-t border-white/[0.06]">
              <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                Safety Permission Mode
              </span>
              <div className="flex items-center space-x-1.5 mt-1">
                <Lock className="h-3.5 w-3.5 text-emerald-400" />
                <span className="font-mono text-emerald-400 text-[11px]">
                  auto_safe (Jailed)
                </span>
              </div>
            </div>

            <div className="pt-3 border-t border-white/[0.08] space-y-2">
              <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                Token & Inference Accounting
              </span>
              <div className="rounded bg-[#080B14] border border-white/[0.06] p-2.5 font-mono text-[11px] space-y-1">
                <div className="flex justify-between text-muted-foreground">
                  <span>Tokens:</span>
                  <span className="text-white font-bold">{formatNumber(totalTokens)}</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>Prompt / Comp:</span>
                  <span className="text-slate-300">{formatNumber(promptTokens)} / {formatNumber(completionTokens)}</span>
                </div>
                <div className="flex justify-between text-muted-foreground pt-1 border-t border-white/[0.04]">
                  <span>Tracked Cost:</span>
                  <span className="text-emerald-400 font-bold">{formatUSD(totalCostUSD)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Center Panel: Agent Execution & Interactive FSM (col-span-5) */}
        <div className="lg:col-span-5 space-y-4">
          {/* FSM Stepper */}
          <Stepper currentState={fsmState} recoveriesCount={recoveriesCount} />

          {/* Active Execution Routine Card */}
          <div className="rounded-md border border-white/[0.08] bg-[#0D1220] p-4 space-y-3 shadow-sm">
            <div className="flex items-center justify-between pb-2 border-b border-white/[0.08]">
              <div className="flex items-center space-x-2">
                <Sparkles className="h-4 w-4 text-cyan-400" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-white font-mono">
                  Active Control Loop
                </h4>
              </div>
              <span className="text-[11px] font-mono text-muted-foreground">
                Step 5 of 20
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center space-x-2">
                <span className="text-muted-foreground font-mono">Current State:</span>
                <span className="font-mono font-bold text-violet-400">{fsmState}</span>
                <span className="text-slate-500 font-mono text-[10px]">
                  (AST-Guided Autonomous Loop)
                </span>
              </div>
              <p className="text-slate-200 text-xs leading-relaxed bg-[#080B14] border border-white/[0.06] p-3 rounded font-mono text-[11px]">
                {fsmState === "DONE"
                  ? "Patch verified successfully against test suite. Snapshot finalized."
                  : fsmState === "FAILED"
                  ? "Recovery retry limit reached (3 attempts). Execution halted safely."
                  : fsmState === "ACT"
                  ? "Applying unified diff patch to src/billing/calculator.py via sandbox patch editor."
                  : "Evaluating AST symbol dependencies and reciprocal rank context chunks."}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/[0.06] text-[11px] font-mono">
              <div className="rounded bg-[#080B14] p-2 border border-white/[0.04]">
                <span className="text-muted-foreground block text-[10px]">Retry Ceiling</span>
                <span className="text-white font-bold">3 attempts</span>
              </div>
              <div className="rounded bg-[#080B14] p-2 border border-white/[0.04]">
                <span className="text-muted-foreground block text-[10px]">Baseline Snapshot</span>
                <span className="text-emerald-400 font-bold">git:a7b841</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel: Live Intelligence (col-span-4) */}
        <div className="lg:col-span-4 rounded-md border border-white/[0.08] bg-[#0D1220] flex flex-col h-[520px] shadow-sm overflow-hidden">
          {/* Tabs Bar */}
          <div className="flex items-center justify-between border-b border-white/[0.08] bg-[#080B14] px-3 py-2 text-xs">
            <div className="flex items-center space-x-1">
              <button
                onClick={() => setActiveTab("events")}
                className={`rounded px-2 py-1 text-xs font-mono font-medium transition ${
                  activeTab === "events"
                    ? "bg-violet-600 text-white font-bold"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                Feed
              </button>
              <button
                onClick={() => setActiveTab("context")}
                className={`rounded px-2 py-1 text-xs font-mono font-medium transition ${
                  activeTab === "context"
                    ? "bg-violet-600 text-white font-bold"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                Context
              </button>
              <button
                onClick={() => setActiveTab("tools")}
                className={`rounded px-2 py-1 text-xs font-mono font-medium transition ${
                  activeTab === "tools"
                    ? "bg-violet-600 text-white font-bold"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                Tools
              </button>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setAutoScroll(!autoScroll)}
                title="Toggle Auto-Scroll"
                className={`text-[10px] font-mono rounded px-1.5 py-0.5 border ${
                  autoScroll ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10" : "border-white/[0.1] text-muted-foreground"
                }`}
              >
                Auto-scroll: {autoScroll ? "ON" : "OFF"}
              </button>
            </div>
          </div>

          {/* Search & Event Filters (Only on feed tab) */}
          {activeTab === "events" && (
            <div className="p-2 border-b border-white/[0.06] bg-[#080B14] space-y-1.5">
              <div className="relative">
                <Search className="h-3 w-3 absolute left-2 top-2 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Filter events..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded bg-[#121A2A] border border-white/[0.08] pl-7 pr-2 py-1 text-[11px] font-mono text-white placeholder:text-muted-foreground focus:outline-none focus:border-violet-500"
                />
              </div>

              <div className="flex items-center space-x-1 text-[10px] font-mono">
                {(["ALL", "THOUGHTS", "TOOLS", "RECOVERY"] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setEventFilter(mode)}
                    className={`rounded px-1.5 py-0.5 transition ${
                      eventFilter === mode
                        ? "bg-white/[0.1] text-white font-bold"
                        : "text-muted-foreground hover:text-white"
                    }`}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Tab Content Area */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2.5 font-mono text-xs">
            {activeTab === "events" && (
              <>
                {filteredEvents.map((evt, idx) => {
                  if (evt.type === "STATE_CHANGE") {
                    return (
                      <div
                        key={idx}
                        className="py-1 px-2 border-l-2 border-violet-500 bg-violet-500/10 rounded-r text-[11px]"
                      >
                        <div className="flex items-center justify-between text-muted-foreground text-[10px]">
                          <span>{evt.timestamp}</span>
                          <span className="font-bold text-violet-300">[{evt.data.state}]</span>
                        </div>
                        <p className="text-slate-200 mt-0.5">{evt.data.reason}</p>
                      </div>
                    );
                  }

                  if (evt.type === "THOUGHT") {
                    return (
                      <div
                        key={idx}
                        className="rounded border border-white/[0.08] bg-[#121A2A] p-2.5 space-y-1"
                      >
                        <div className="flex items-center justify-between text-[10px] text-cyan-400 font-semibold">
                          <span>Hypothesis (Step {evt.step})</span>
                          <span className="text-muted-foreground">{evt.timestamp}</span>
                        </div>
                        <p className="font-sans text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                          {evt.data.thought}
                        </p>
                      </div>
                    );
                  }

                  if (evt.type === "TOOL_CALL") {
                    const callId = evt.data.id || `call_${idx}`;
                    const isExpanded = expandedCalls[callId] ?? false;
                    return (
                      <div
                        key={idx}
                        className="rounded border border-white/[0.08] bg-[#080B14] p-2 text-[11px]"
                      >
                        <div
                          onClick={() => toggleAccordion(callId)}
                          className="flex items-center justify-between cursor-pointer select-none"
                        >
                          <div className="flex items-center space-x-1.5">
                            {isExpanded ? <ChevronDown className="h-3 w-3 text-violet-400" /> : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                            <span className="font-bold text-white">{evt.data.tool}</span>
                          </div>
                          <span className="text-[10px] text-emerald-400 font-mono">
                            {evt.data.status || "INVOKED"}
                          </span>
                        </div>

                        {isExpanded && (
                          <div className="mt-2 pt-2 border-t border-white/[0.06] text-[10px] space-y-1">
                            <span className="text-muted-foreground block">Arguments:</span>
                            <pre className="bg-[#121A2A] p-1.5 rounded overflow-x-auto text-slate-300">
                              {JSON.stringify(evt.data.arguments || {}, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    );
                  }

                  if (evt.type === "TOOL_RESULT") {
                    return (
                      <div
                        key={idx}
                        className="rounded border border-white/[0.06] bg-[#080B14] p-2 text-[11px]"
                      >
                        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                          <span className="text-emerald-400 font-bold">TOOL_RESULT</span>
                          <span>{evt.timestamp}</span>
                        </div>
                        <pre className="mt-1 text-[10px] text-slate-300 font-mono overflow-x-auto">
                          {evt.data.output || "Success"}
                        </pre>
                      </div>
                    );
                  }

                  return (
                    <div key={idx} className="p-1.5 text-[10px] text-muted-foreground">
                      [{evt.type}] {JSON.stringify(evt.data)}
                    </div>
                  );
                })}
                <div ref={feedEndRef} />
              </>
            )}

            {activeTab === "context" && (
              <div className="space-y-2">
                <span className="text-[11px] font-mono text-muted-foreground block">
                  Scored Retrieval Chunks (Adaptive Knee-Curve):
                </span>
                {MOCK_RETRIEVED_CHUNKS.map((chunk, idx) => (
                  <div
                    key={idx}
                    className="rounded border border-white/[0.08] bg-[#080B14] p-2.5 text-[11px] space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white truncate max-w-[180px]">{chunk.file_path}</span>
                      <span className="font-mono text-cyan-400 text-[10px]">Score: {chunk.score.toFixed(3)}</span>
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono">
                      Lines {chunk.start_line} - {chunk.end_line} ({chunk.method})
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === "tools" && (
              <div className="space-y-2 text-xs">
                <span className="text-[11px] font-mono text-muted-foreground block">
                  Audited Tool Invocations:
                </span>
                <div className="rounded border border-white/[0.08] bg-[#080B14] p-2.5 space-y-1 font-mono text-[11px]">
                  <div className="flex justify-between text-white font-bold">
                    <span>read_file</span>
                    <span className="text-emerald-400">ALLOW</span>
                  </div>
                  <span className="text-muted-foreground text-[10px]">Path: src/billing/calculator.py</span>
                </div>
                <div className="rounded border border-white/[0.08] bg-[#080B14] p-2.5 space-y-1 font-mono text-[11px]">
                  <div className="flex justify-between text-white font-bold">
                    <span>apply_patch</span>
                    <span className="text-emerald-400">ALLOW</span>
                  </div>
                  <span className="text-muted-foreground text-[10px]">Path: src/billing/calculator.py (4 lines)</span>
                </div>
                <div className="rounded border border-white/[0.08] bg-[#080B14] p-2.5 space-y-1 font-mono text-[11px]">
                  <div className="flex justify-between text-white font-bold">
                    <span>run_command</span>
                    <span className="text-amber-400">PROMPT</span>
                  </div>
                  <span className="text-muted-foreground text-[10px]">Cmd: pytest tests/test_calculator.py</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Section: Code Review Workspace with Monaco Diff Viewer */}
      <section className="space-y-3 pt-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <FileCode2 className="h-4 w-4 text-violet-400" />
              <span>Code Review & Verification Workspace</span>
            </h3>
            <p className="text-xs text-muted-foreground">
              Review AST-synthesized patches side-by-side against the baseline repository snapshot.
            </p>
          </div>

          <div className="flex items-center space-x-1 text-xs">
            <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded">
              VERIFICATION: 14/14 TESTS PASSING
            </span>
          </div>
        </div>

        {/* Diff Viewer */}
        <DiffViewer
          original={diffOriginal}
          modified={diffModified}
          filename={activeDiffFile}
          language="python"
        />
      </section>
    </div>
  );
}
