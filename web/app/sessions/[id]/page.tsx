"use client";

import React, { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
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
  const taskTitle = sessionMeta?.task || "Autonomous code repair and verification task";

  // Event stream state
  const [events, setEvents] = useState<MockAgentEvent[]>([]);
  const [eventFilter, setEventFilter] = useState<string>("ALL");
  const [fsmState, setFsmState] = useState<FSMState>("ANALYZE");
  const [recoveriesCount, setRecoveriesCount] = useState(0);
  const [sessionStatus, setSessionStatus] = useState<string>("RUNNING");
  const [activeTab, setActiveTab] = useState<"diff" | "context" | "cost">("diff");

  // Diff state
  const [diffOriginal, setDiffOriginal] = useState(MOCK_DIFF_ORIGINAL);
  const [diffModified, setDiffModified] = useState(MOCK_DIFF_MODIFIED);

  // Approval state
  const [approvalPending, setApprovalPending] = useState(false);

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
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const toggleAccordion = (id: string) => {
    setExpandedCalls((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredEvents = events.filter((e) => {
    if (eventFilter === "ALL") return true;
    if (eventFilter === "THOUGHTS") return e.type === "THOUGHT";
    if (eventFilter === "TOOLS") return e.type === "TOOL_CALL" || e.type === "TOOL_RESULT";
    if (eventFilter === "RECOVERY") return e.type === "RECOVERY";
    if (eventFilter === "STATE") return e.type === "STATE_CHANGE";
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
    <div className="space-y-6">
      {/* Demo Notice Banner */}
      <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3.5 flex items-start space-x-3 text-xs">
        <span className="rounded bg-amber-500/20 px-2 py-0.5 font-mono text-[10px] font-semibold text-amber-700 dark:text-amber-300 uppercase tracking-wider shrink-0 mt-0.5">
          DEMO DATA
        </span>
        <div className="text-muted-foreground leading-relaxed">
          <span className="font-semibold text-foreground">Interactive Session Demonstration:</span> This view displays recorded trace events, tool invocations, and diff inspection for verification and UI review. For live agent runs on local repositories, connect the FastAPI backend and start a run via the CLI or dashboard.
        </div>
      </div>

      {/* Session Header and Controls Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-md border border-border bg-card p-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-base font-bold text-foreground font-mono">{sessionId}</h1>
            <span
              className={`rounded px-2 py-0.5 text-xs font-semibold ${
                sessionStatus === "COMPLETED"
                  ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30"
                  : sessionStatus === "RUNNING"
                  ? "bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-500/30 animate-pulse"
                  : sessionStatus === "PAUSED"
                  ? "bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30"
                  : "bg-red-500/15 text-red-700 dark:text-red-300 border border-red-500/30"
              }`}
            >
              {sessionStatus}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {taskTitle}
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2">
          {sessionStatus === "RUNNING" ? (
            <button
              onClick={handlePause}
              className="flex items-center space-x-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted transition"
            >
              <Pause className="h-3.5 w-3.5" />
              <span>Pause</span>
            </button>
          ) : (
            <button
              onClick={handleResume}
              className="flex items-center space-x-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted transition"
            >
              <Play className="h-3.5 w-3.5" />
              <span>Resume</span>
            </button>
          )}

          <button
            onClick={handleStop}
            className="flex items-center space-x-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 transition"
          >
            <Square className="h-3.5 w-3.5" />
            <span>Stop</span>
          </button>

          <button
            onClick={handleRollback}
            className="flex items-center space-x-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Rollback Baseline</span>
          </button>
        </div>
      </div>

      {/* FSM Stepper */}
      <Stepper currentState={fsmState} recoveriesCount={recoveriesCount} />

      {/* Human Approval Alert Banner (when requested) */}
      {approvalPending && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-md border border-amber-500/40 bg-amber-500/10 p-4">
          <div className="flex items-start space-x-3">
            <ShieldAlert className="h-5 w-5 text-amber-500 mt-0.5" />
            <div>
              <h4 className="text-xs font-bold text-foreground uppercase tracking-wider">
                Human-in-the-Loop Approval Required
              </h4>
              <p className="text-xs text-muted-foreground mt-0.5">
                The agent is requesting permission to execute shell command:{" "}
                <code className="rounded bg-muted px-1 py-0.5 font-mono text-foreground">
                  pytest tests/test_calculator.py
                </code>
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleApproval(false)}
              className="rounded-md border border-border bg-background px-3 py-1.5 text-xs font-semibold text-destructive hover:bg-muted transition"
            >
              Reject Action
            </button>
            <button
              onClick={() => handleApproval(true)}
              className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition"
            >
              Approve Execution
            </button>
          </div>
        </div>
      )}

      {/* Main Split Pane Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[600px]">
        {/* Left Pane: Real-Time Event Feed */}
        <div className="lg:col-span-5 flex flex-col rounded-md border border-border bg-card overflow-hidden">
          {/* Feed Filter Bar */}
          <div className="flex items-center justify-between border-b border-border bg-muted/40 px-4 py-2.5">
            <div className="flex items-center space-x-2">
              <Terminal className="h-4 w-4 text-primary" />
              <span className="text-xs font-semibold text-foreground">Live SSE Event Feed</span>
            </div>
            <div className="flex items-center space-x-1 text-[11px]">
              {(["ALL", "THOUGHTS", "TOOLS", "RECOVERY"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setEventFilter(mode)}
                  className={`rounded-md px-2 py-0.5 font-mono transition ${
                    eventFilter === mode
                      ? "bg-primary text-primary-foreground font-bold"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>

          {/* Events List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-xs max-h-[600px]">
            {filteredEvents.map((evt, idx) => {
              if (evt.type === "STATE_CHANGE") {
                return (
                  <div
                    key={idx}
                    className="flex items-center space-x-2 text-muted-foreground py-1 border-l-2 border-primary pl-2.5 bg-muted/20 rounded-r"
                  >
                    <span className="text-[10px]">{evt.timestamp}</span>
                    <span className="font-bold text-foreground">[{evt.data.state}]</span>
                    <span>{evt.data.reason}</span>
                  </div>
                );
              }

              if (evt.type === "THOUGHT") {
                return (
                  <div
                    key={idx}
                    className="rounded-md border border-border bg-muted/30 p-3 text-foreground"
                  >
                    <div className="flex items-center space-x-1.5 text-[11px] font-semibold text-primary mb-1">
                      <span>Reasoning Hypothesis (Step {evt.step})</span>
                    </div>
                    <p className="font-sans text-xs leading-relaxed text-foreground whitespace-pre-wrap">
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
                    className="rounded-md border border-border bg-card p-3 transition"
                  >
                    <div
                      onClick={() => toggleAccordion(callId)}
                      className="flex items-center justify-between cursor-pointer select-none"
                    >
                      <div className="flex items-center space-x-2">
                        {isExpanded ? (
                          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                        <span className="font-bold text-foreground">{evt.data.name}</span>
                        <span className="text-[10px] text-muted-foreground">{callId}</span>
                      </div>
                      <span className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                        invoked
                      </span>
                    </div>

                    {isExpanded && (
                      <div className="mt-2.5 pt-2 border-t border-border">
                        <span className="text-[10px] text-muted-foreground block mb-1">Arguments:</span>
                        <pre className="rounded border border-border bg-muted/50 p-2 text-[11px] text-foreground overflow-x-auto">
                          {JSON.stringify(evt.data.arguments, null, 2)}
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
                    className="rounded-md border border-border bg-card p-2.5 text-xs pl-3 border-l-4 border-l-primary"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-foreground">{evt.data.tool_name} Result</span>
                      <span className="text-[10px] text-muted-foreground">{evt.data.duration_ms} ms</span>
                    </div>
                    <pre className="text-[11px] text-muted-foreground overflow-x-auto whitespace-pre-wrap max-h-24">
                      {evt.data.output}
                    </pre>
                  </div>
                );
              }

              return null;
            })}
            <div ref={feedEndRef} />
          </div>
        </div>

        {/* Right Pane: Tabbed Workspace Inspector */}
        <div className="lg:col-span-7 flex flex-col rounded-md border border-border bg-card overflow-hidden">
          {/* Tabs Header */}
          <div className="flex border-b border-border bg-muted/40 px-2 pt-1">
            <button
              onClick={() => setActiveTab("diff")}
              className={`flex items-center space-x-1.5 border-b-2 px-4 py-2 text-xs font-medium transition ${
                activeTab === "diff"
                  ? "border-primary text-foreground font-semibold"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <FileCode2 className="h-4 w-4" />
              <span>Workspace Diff</span>
            </button>

            <button
              onClick={() => setActiveTab("context")}
              className={`flex items-center space-x-1.5 border-b-2 px-4 py-2 text-xs font-medium transition ${
                activeTab === "context"
                  ? "border-primary text-foreground font-semibold"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Database className="h-4 w-4" />
              <span>Retrieved Context ({MOCK_RETRIEVED_CHUNKS.length})</span>
            </button>

            <button
              onClick={() => setActiveTab("cost")}
              className={`flex items-center space-x-1.5 border-b-2 px-4 py-2 text-xs font-medium transition ${
                activeTab === "cost"
                  ? "border-primary text-foreground font-semibold"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Coins className="h-4 w-4" />
              <span>Cost Ledger</span>
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 p-4">
            {activeTab === "diff" && (
              <DiffViewer
                original={diffOriginal}
                modified={diffModified}
                filename="src/billing/calculator.py"
              />
            )}

            {activeTab === "context" && (
              <div className="space-y-4">
                <div className="rounded-md border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground">Adaptive Hybrid Retrieval:</span> Fused BM25 lexical
                  and all-MiniLM-L6-v2 dense embeddings with 1-hop graph neighbor expansion.
                </div>

                <div className="space-y-3">
                  {MOCK_RETRIEVED_CHUNKS.map((chunk, idx) => (
                    <div
                      key={idx}
                      className="rounded-md border border-border bg-card p-3 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="font-mono font-bold text-foreground text-xs">
                            {chunk.file_path}
                          </span>
                          <span className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                            Lines {chunk.start_line} to {chunk.end_line}
                          </span>
                        </div>
                        <span className="rounded border border-border bg-muted px-2 py-0.5 font-mono text-[10px] font-bold text-foreground">
                          Score: {chunk.score.toFixed(4)}
                        </span>
                      </div>

                      <div className="text-[11px] text-muted-foreground font-mono">
                        Method: {chunk.method}
                      </div>

                      <pre className="rounded border border-border bg-muted/40 p-2.5 font-mono text-xs text-foreground overflow-x-auto">
                        {chunk.code}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === "cost" && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-md border border-border bg-muted/20 p-4">
                    <span className="text-xs text-muted-foreground block">Total Tokens Used</span>
                    <span className="text-2xl font-bold font-mono text-foreground mt-1 block">
                      {formatNumber(totalTokens)}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      Prompt: {formatNumber(promptTokens)}, Completion: {formatNumber(completionTokens)}
                    </span>
                  </div>

                  <div className="rounded-md border border-border bg-muted/20 p-4">
                    <span className="text-xs text-muted-foreground block">Estimated Cost (USD)</span>
                    <span className="text-2xl font-bold font-mono text-foreground mt-1 block">
                      {formatUSD(totalCostUSD)}
                    </span>
                    <span className="text-[11px] text-muted-foreground">Pricing Table: deepseek-coder</span>
                  </div>
                </div>

                <div className="rounded-md border border-border bg-muted/20 p-4 space-y-3">
                  <h4 className="text-xs font-semibold text-foreground">Budget Limit Policies</h4>
                  <div className="grid grid-cols-2 gap-3 text-xs text-muted-foreground">
                    <div>Step Cap: <span className="font-mono text-foreground">20 steps</span></div>
                    <div>Cost Ceiling: <span className="font-mono text-foreground">$0.50</span></div>
                    <div>Wall Timeout: <span className="font-mono text-foreground">300 sec</span></div>
                    <div>Token Cap: <span className="font-mono text-foreground">100,000 tok</span></div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
