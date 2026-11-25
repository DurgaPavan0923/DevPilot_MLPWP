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
  BookOpen,
  Code2,
  ToggleLeft,
  ToggleRight,
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
    { name: "Home", href: "/", icon: Layers },
    { name: "Product", href: "/product", icon: Code2 },
    { name: "Live Session", href: "/sessions", icon: Terminal },
    { name: "Repo Explorer", href: "/repo", icon: FolderGit2 },
    { name: "Evaluation Lab", href: "/eval", icon: BarChart3 },
    { name: "Docs", href: "/docs", icon: BookOpen },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-primary text-primary-foreground">
              <Cpu className="h-4 w-4" />
            </div>
            <span className="font-bold text-base tracking-tight text-foreground">DevPilot</span>
            <span className="hidden sm:inline-flex items-center rounded border border-primary/20 bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
              Research Harness
            </span>
          </Link>

          <nav className="hidden md:flex space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center space-x-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center space-x-2.5">
          {/* Mock API Toggle */}
          <button
            onClick={handleToggleMock}
            title="Toggle between real FastAPI backend and deterministic mock fixtures"
            className="flex items-center space-x-1.5 rounded-md border border-border bg-card px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:border-slate-400 transition"
          >
            {mock ? (
              <ToggleRight className="h-4 w-4 text-emerald-600" />
            ) : (
              <ToggleLeft className="h-4 w-4 text-muted-foreground" />
            )}
            <span className="font-mono text-[11px]">Mock Mode: {mock ? "ON" : "OFF"}</span>
          </button>

          {/* Backend Health Badge */}
          <div className="flex items-center space-x-1.5 rounded-md border border-border bg-card px-2 py-1 text-xs font-medium">
            <span
              className={`h-2 w-2 rounded-full ${
                health.status === "healthy" ? "bg-emerald-500 animate-pulse" : "bg-amber-500"
              }`}
            />
            <span className="text-muted-foreground text-[11px] capitalize">{health.status}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
