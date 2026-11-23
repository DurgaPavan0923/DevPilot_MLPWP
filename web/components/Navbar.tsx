"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Cpu,
  Layers,
  BarChart3,
  FolderGit2,
  Terminal,
  Activity,
  ToggleLeft,
  ToggleRight,
  ShieldCheck,
} from "lucide-react";
import { fetchHealth, isMockMode, setMockMode } from "@/lib/api";

export function Navbar() {
  const pathname = usePathname();
  const [mock, setMock] = useState(false);
  const [health, setHealth] = useState<{ status: string; version: string }>({
    status: "checking...",
    version: "",
  });

  useEffect(() => {
    setMock(isMockMode());
    fetchHealth().then((h) => setHealth(h));
  }, []);

  const handleToggleMock = () => {
    const nextVal = !mock;
    setMock(nextVal);
    setMockMode(nextVal);
  };

  const navItems = [
    { name: "Dashboard", href: "/", icon: Layers },
    { name: "Live Session", href: "/sessions/sess_demo_alpha_92", icon: Terminal },
    { name: "Repo Explorer", href: "/repo", icon: FolderGit2 },
    { name: "Evaluation Lab", href: "/eval", icon: BarChart3 },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white shadow-md shadow-blue-500/20">
              <Cpu className="h-5 w-5" />
            </div>
            <span className="font-bold text-lg tracking-tight text-white">DevPilot</span>
            <span className="hidden sm:inline-flex items-center rounded-full bg-blue-950/80 px-2 py-0.5 text-xs font-semibold text-blue-400 border border-blue-800/60">
              Research Harness
            </span>
          </Link>

          <nav className="hidden md:flex space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center space-x-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-slate-800 text-blue-400"
                      : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center space-x-3">
          {/* Mock API Toggle */}
          <button
            onClick={handleToggleMock}
            title="Toggle between real FastAPI backend and deterministic mock fixtures"
            className="flex items-center space-x-1.5 rounded-lg border border-border bg-slate-900/80 px-2.5 py-1 text-xs text-slate-300 hover:border-slate-700 transition"
          >
            {mock ? (
              <ToggleRight className="h-4 w-4 text-emerald-400" />
            ) : (
              <ToggleLeft className="h-4 w-4 text-slate-500" />
            )}
            <span className="font-mono">Mock Mode: {mock ? "ON" : "OFF"}</span>
          </button>

          {/* Backend Health Pill */}
          <div className="flex items-center space-x-1.5 rounded-full border border-border bg-slate-900 px-2.5 py-1 text-xs font-medium">
            <span
              className={`h-2 w-2 rounded-full ${
                health.status === "healthy" ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
              }`}
            />
            <span className="text-slate-300 capitalize">{health.status}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
