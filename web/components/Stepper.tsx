"use client";

import React from "react";
import {
  CheckCircle2,
  Circle,
  AlertTriangle,
  XCircle,
  Loader2,
  Sparkles,
} from "lucide-react";

export type FSMState =
  | "INIT"
  | "ANALYZE"
  | "RETRIEVE"
  | "PLAN"
  | "ACT"
  | "OBSERVE"
  | "RECOVER"
  | "VERIFY"
  | "DONE"
  | "FAILED";

interface StepperProps {
  currentState: FSMState;
  recoveriesCount?: number;
}

const ORDERED_STATES: FSMState[] = [
  "INIT",
  "ANALYZE",
  "RETRIEVE",
  "PLAN",
  "ACT",
  "OBSERVE",
  "VERIFY",
  "DONE",
];

export function Stepper({ currentState, recoveriesCount = 0 }: StepperProps) {
  const currentIndex = ORDERED_STATES.indexOf(currentState);
  const isFailed = currentState === "FAILED";
  const isRecovering = currentState === "RECOVER";

  return (
    <div className="w-full rounded-md border border-white/[0.08] bg-[#0D1220] p-4 shadow-sm">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-white/[0.08] mb-3 gap-2">
        <div className="flex items-center space-x-2.5">
          <span className="text-[11px] uppercase font-mono font-semibold tracking-wider text-muted-foreground">
            Finite State Machine:
          </span>
          <span
            className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
              isFailed
                ? "bg-red-500/15 text-red-400 border border-red-500/30"
                : currentState === "DONE"
                ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                : isRecovering
                ? "bg-amber-500/15 text-amber-300 border border-amber-500/30 animate-pulse"
                : "bg-violet-500/15 text-violet-300 border border-violet-500/30 shadow-sm shadow-violet-500/20 animate-pulse"
            }`}
          >
            {currentState}
          </span>
        </div>

        {recoveriesCount > 0 && (
          <div className="flex items-center space-x-1.5 text-xs text-amber-300 bg-amber-500/10 px-2.5 py-0.5 rounded border border-amber-500/30 font-mono">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
            <span>Recoveries Engaged: {recoveriesCount}</span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between overflow-x-auto py-2">
        {ORDERED_STATES.map((state, idx) => {
          let status: "completed" | "current" | "pending" | "failed" | "recovery" = "pending";

          if (isFailed && state === "DONE") {
            status = "failed";
          } else if (state === currentState) {
            status = "current";
          } else if (currentIndex >= 0 && idx < currentIndex) {
            status = "completed";
          }

          if (isRecovering && state === "OBSERVE") {
            status = "recovery";
          }

          return (
            <div key={state} className="flex flex-1 items-center min-w-[70px]">
              <div className="flex flex-col items-center flex-1">
                <div className="relative flex items-center justify-center">
                  {status === "completed" && (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  )}
                  {status === "current" && (
                    <div className="relative flex items-center justify-center">
                      <div className="absolute h-5 w-5 rounded-full bg-violet-500/20 animate-ping" />
                      <Loader2 className="h-4 w-4 text-violet-400 animate-spin" />
                    </div>
                  )}
                  {status === "recovery" && (
                    <AlertTriangle className="h-4 w-4 text-amber-400 animate-bounce" />
                  )}
                  {status === "failed" && <XCircle className="h-4 w-4 text-red-400" />}
                  {status === "pending" && <Circle className="h-3.5 w-3.5 text-slate-600" />}
                </div>
                <span
                  className={`mt-1.5 text-[10px] font-mono tracking-tight ${
                    status === "current"
                      ? "text-violet-400 font-bold"
                      : status === "completed"
                      ? "text-slate-300 font-medium"
                      : status === "recovery"
                      ? "text-amber-400 font-bold"
                      : "text-slate-500"
                  }`}
                >
                  {state}
                </span>
              </div>
              {idx < ORDERED_STATES.length - 1 && (
                <div
                  className={`h-[1px] flex-1 mx-1 ${
                    currentIndex > idx
                      ? "bg-emerald-500/40"
                      : currentIndex === idx
                      ? "bg-violet-500/40"
                      : "bg-white/[0.06]"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
