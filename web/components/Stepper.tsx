"use client";

import React from "react";
import {
  CheckCircle2,
  Circle,
  AlertTriangle,
  XCircle,
  Loader2,
  ShieldAlert,
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
    <div className="w-full rounded-xl border border-border bg-slate-900/60 p-4 shadow-sm">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-slate-800 mb-3 gap-2">
        <div className="flex items-center space-x-2">
          <span className="text-xs uppercase font-semibold tracking-wider text-slate-400">
            FSM State Machine:
          </span>
          <span
            className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
              isFailed
                ? "bg-rose-950 text-rose-300 border border-rose-800"
                : currentState === "DONE"
                ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                : isRecovering
                ? "bg-amber-950 text-amber-300 border border-amber-800 animate-pulse"
                : "bg-blue-950 text-blue-300 border border-blue-800 animate-pulse"
            }`}
          >
            {currentState}
          </span>
        </div>

        {recoveriesCount > 0 && (
          <div className="flex items-center space-x-1.5 text-xs text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/40">
            <AlertTriangle className="h-3.5 w-3.5" />
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
                    <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                  )}
                  {status === "current" && (
                    <div className="relative">
                      <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />
                      <span className="absolute inset-0 rounded-full bg-blue-500/20 animate-ping" />
                    </div>
                  )}
                  {status === "recovery" && (
                    <AlertTriangle className="h-5 w-5 text-amber-400 animate-bounce" />
                  )}
                  {status === "failed" && <XCircle className="h-5 w-5 text-rose-400" />}
                  {status === "pending" && <Circle className="h-4 w-4 text-slate-600" />}
                </div>
                <span
                  className={`mt-1.5 text-[10px] font-mono tracking-tight font-medium ${
                    status === "current"
                      ? "text-blue-300 font-bold"
                      : status === "completed"
                      ? "text-slate-300"
                      : status === "recovery"
                      ? "text-amber-300 font-bold"
                      : "text-slate-500"
                  }`}
                >
                  {state}
                </span>
              </div>
              {idx < ORDERED_STATES.length - 1 && (
                <div
                  className={`h-0.5 flex-1 mx-1 ${
                    currentIndex > idx
                      ? "bg-emerald-500/60"
                      : currentIndex === idx
                      ? "bg-blue-500/40"
                      : "bg-slate-800"
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
