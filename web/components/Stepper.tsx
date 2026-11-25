"use client";

import React from "react";
import {
  CheckCircle2,
  Circle,
  AlertTriangle,
  XCircle,
  Loader2,
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
    <div className="w-full rounded-md border border-border bg-card p-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border mb-3 gap-2">
        <div className="flex items-center space-x-2">
          <span className="text-xs uppercase font-semibold tracking-wider text-muted-foreground">
            FSM State Machine:
          </span>
          <span
            className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
              isFailed
                ? "bg-destructive/15 text-destructive border border-destructive/30"
                : currentState === "DONE"
                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30"
                : isRecovering
                ? "bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30 animate-pulse"
                : "bg-primary/15 text-primary border border-primary/30 animate-pulse"
            }`}
          >
            {currentState}
          </span>
        </div>

        {recoveriesCount > 0 && (
          <div className="flex items-center space-x-1.5 text-xs text-amber-700 dark:text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
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
                    <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  )}
                  {status === "current" && (
                    <div className="relative">
                      <Loader2 className="h-5 w-5 text-primary animate-spin" />
                    </div>
                  )}
                  {status === "recovery" && (
                    <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 animate-bounce" />
                  )}
                  {status === "failed" && <XCircle className="h-5 w-5 text-destructive" />}
                  {status === "pending" && <Circle className="h-4 w-4 text-muted-foreground/40" />}
                </div>
                <span
                  className={`mt-1.5 text-[10px] font-mono tracking-tight font-medium ${
                    status === "current"
                      ? "text-primary font-bold"
                      : status === "completed"
                      ? "text-foreground"
                      : status === "recovery"
                      ? "text-amber-600 dark:text-amber-300 font-bold"
                      : "text-muted-foreground"
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
                      ? "bg-primary/40"
                      : "bg-border"
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
