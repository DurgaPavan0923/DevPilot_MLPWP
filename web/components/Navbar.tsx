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
  Play,
  Menu,
  X,
  ToggleLeft,
  ToggleRight,
  Sparkles,
} from "lucide-react";

function GithubIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      stroke="currentColor"
      strokeWidth="2"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}
import { fetchHealth, isMockMode, setMockMode } from "@/lib/api";

export function Navbar() {
  const pathname = usePathname();
  const [mock, setMock] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
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
    { name: "Overview", href: "/", icon: Layers },
    { name: "Product", href: "/product", icon: Code2 },
    { name: "Live Session", href: "/sessions", icon: Terminal },
    { name: "Repository Explorer", href: "/repo", icon: FolderGit2 },
    { name: "Evaluation Lab", href: "/eval", icon: BarChart3 },
    { name: "Documentation", href: "/docs", icon: BookOpen },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.08] bg-[#080B14]/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Left: Brand Identity */}
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="relative flex h-8 w-8 items-center justify-center rounded-md border border-violet-500/30 bg-violet-500/10 text-violet-400 shadow-sm shadow-violet-500/20 group-hover:border-violet-500/50 group-hover:bg-violet-500/20 transition-all">
              <Cpu className="h-4 w-4" />
              <div className="absolute -top-0.5 -right-0.5 h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping opacity-75" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base tracking-tight text-foreground">DevPilot</span>
                <span className="inline-flex items-center rounded border border-violet-500/30 bg-violet-500/10 px-1.5 py-0.5 text-[10px] font-mono font-medium text-violet-300">
                  v2.0
                </span>
              </div>
              <span className="hidden sm:inline-block text-[10px] text-muted-foreground font-mono">
                Autonomous Coding Harness
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden lg:flex items-center space-x-1">
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
                  className={`relative flex items-center space-x-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                    isActive
                      ? "text-white bg-white/[0.06] border border-white/[0.1] shadow-inner"
                      : "text-muted-foreground hover:text-foreground hover:bg-white/[0.03]"
                  }`}
                >
                  <Icon className={`h-3.5 w-3.5 ${isActive ? "text-violet-400" : "text-muted-foreground"}`} />
                  <span>{item.name}</span>
                  {isActive && (
                    <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-gradient-to-r from-violet-500 to-cyan-400 rounded-full" />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Actions & Status Controls */}
        <div className="hidden sm:flex items-center space-x-3">
          {/* Mock Mode Toggle */}
          <button
            onClick={handleToggleMock}
            title="Toggle between live backend and deterministic demonstration fixtures"
            className="flex items-center space-x-1.5 rounded-md border border-white/[0.08] bg-[#0D1220] px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground hover:border-violet-500/40 transition"
          >
            {mock ? (
              <ToggleRight className="h-4 w-4 text-emerald-400" />
            ) : (
              <ToggleLeft className="h-4 w-4 text-muted-foreground" />
            )}
            <span className="font-mono text-[11px]">Demo Fixtures: {mock ? "ON" : "OFF"}</span>
          </button>

          {/* Backend Connection Indicator */}
          <div className="flex items-center space-x-1.5 rounded-md border border-white/[0.08] bg-[#0D1220] px-2.5 py-1 text-xs font-mono">
            <span
              className={`h-2 w-2 rounded-full ${
                health.status === "healthy"
                  ? "bg-emerald-400 shadow-sm shadow-emerald-400/50 animate-pulse"
                  : "bg-amber-400 shadow-sm shadow-amber-400/50"
              }`}
            />
            <span className="text-muted-foreground text-[11px] capitalize">
              {health.status === "healthy" ? "API Online" : "Demo Mode"}
            </span>
          </div>

          {/* GitHub Repository Link */}
          <a
            href="https://github.com/DurgaPavan0923/DevPilot_MLPWP"
            target="_blank"
            rel="noreferrer"
            aria-label="GitHub Repository"
            className="flex h-8 w-8 items-center justify-center rounded-md border border-white/[0.08] bg-[#0D1220] text-muted-foreground hover:text-foreground hover:border-white/[0.2] transition"
          >
            <GithubIcon className="h-4 w-4" />
          </a>

          {/* Primary CTA: Launch Workspace */}
          <Link
            href="/sessions"
            className="inline-flex items-center space-x-1.5 rounded-md bg-violet-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm shadow-violet-600/30 hover:bg-violet-500 transition active:scale-[0.98]"
          >
            <Play className="h-3 w-3 fill-current" />
            <span>Launch Workspace</span>
          </Link>
        </div>

        {/* Mobile Hamburger Button */}
        <div className="flex items-center space-x-2 sm:hidden">
          <Link
            href="/sessions"
            className="inline-flex items-center space-x-1 rounded-md bg-violet-600 px-2.5 py-1 text-xs font-semibold text-white"
          >
            <Play className="h-3 w-3 fill-current" />
            <span>Launch</span>
          </Link>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
            className="flex h-8 w-8 items-center justify-center rounded-md border border-white/[0.08] bg-[#0D1220] text-muted-foreground hover:text-foreground"
          >
            {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="border-b border-white/[0.08] bg-[#080B14] px-4 py-4 sm:hidden space-y-3">
          <nav className="flex flex-col space-y-1">
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
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center space-x-2 rounded-md px-3 py-2 text-xs font-medium transition ${
                    isActive
                      ? "bg-white/[0.08] text-white font-semibold"
                      : "text-muted-foreground hover:bg-white/[0.04] hover:text-foreground"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? "text-violet-400" : "text-muted-foreground"}`} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          <div className="pt-3 border-t border-white/[0.08] flex items-center justify-between text-xs">
            <button
              onClick={handleToggleMock}
              className="flex items-center space-x-1.5 text-muted-foreground"
            >
              {mock ? (
                <ToggleRight className="h-4 w-4 text-emerald-400" />
              ) : (
                <ToggleLeft className="h-4 w-4 text-muted-foreground" />
              )}
              <span className="font-mono text-[11px]">Demo Mode: {mock ? "ON" : "OFF"}</span>
            </button>

            <div className="flex items-center space-x-1.5 font-mono text-[11px] text-muted-foreground">
              <span
                className={`h-2 w-2 rounded-full ${
                  health.status === "healthy" ? "bg-emerald-400" : "bg-amber-400"
                }`}
              />
              <span>{health.status === "healthy" ? "API Connected" : "Demo Mode"}</span>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
