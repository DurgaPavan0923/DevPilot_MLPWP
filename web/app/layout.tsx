import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import Link from "next/link";
import { Cpu, ShieldCheck, Database, Terminal, ArrowRight } from "lucide-react";

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

export const metadata: Metadata = {
  title: "DevPilot: Autonomous Coding Agent Harness",
  description:
    "Engineering intelligence for autonomous software development. DevPilot understands your repository, retrieves the right context, executes code in a secure environment, recovers from failures and verifies every change.",
  metadataBase: new URL("https://devpilot.site"),
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon.svg", type: "image/svg+xml" },
    ],
    apple: "/apple-touch-icon.png",
  },
  openGraph: {
    title: "DevPilot: Autonomous Coding Agent Harness",
    description:
      "Engineering intelligence for autonomous software development. Context-aware retrieval, bounded error recovery, sandboxed execution, and automated verification.",
    url: "https://devpilot.site",
    siteName: "DevPilot",
    images: [
      {
        url: "/apple-touch-icon.png",
        width: 180,
        height: 180,
        alt: "DevPilot Logo",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#080B14] font-sans antialiased text-[#F8FAFC] flex flex-col justify-between selection:bg-violet-500/30 selection:text-white">
        <div className="relative flex-1">
          {/* Ambient Lighting & Grid */}
          <div className="pointer-events-none absolute inset-0 bg-grid-pattern opacity-40 z-0" />
          <div className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[450px] radial-glow-hero z-0" />

          {/* Sticky Navigation */}
          <div className="relative z-10">
            <Navbar />
            <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">{children}</main>
          </div>
        </div>

        {/* Global Footer */}
        <footer className="relative z-10 border-t border-white/[0.08] bg-[#080B14] py-12 text-xs text-muted-foreground">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
              {/* Product Info */}
              <div className="space-y-3 md:col-span-1">
                <div className="flex items-center space-x-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded bg-violet-600/20 text-violet-400 border border-violet-500/30">
                    <Cpu className="h-3.5 w-3.5" />
                  </div>
                  <span className="font-bold text-foreground text-sm tracking-tight">DevPilot</span>
                  <span className="font-mono text-[10px] text-violet-400 border border-violet-500/30 bg-violet-500/10 px-1 rounded">
                    v2.0
                  </span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Autonomous coding agent harness with repository-aware context, sandboxed tool execution, bounded recovery, and automated verification.
                </p>
                <div className="pt-1 flex items-center space-x-3 text-muted-foreground">
                  <a
                    href="https://github.com/DurgaPavan0923/DevPilot_MLPWP"
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-foreground transition-colors"
                  >
                    <GithubIcon className="h-4 w-4" />
                  </a>
                </div>
              </div>

              {/* Subsystems */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground">
                  Architecture
                </h4>
                <ul className="space-y-1.5 text-xs">
                  <li>
                    <Link href="/product#llm-provider" className="hover:text-foreground transition-colors">
                      LLM Provider Layer
                    </Link>
                  </li>
                  <li>
                    <Link href="/product#context-engine" className="hover:text-foreground transition-colors">
                      Context Retrieval Engine
                    </Link>
                  </li>
                  <li>
                    <Link href="/product#agent-runtime" className="hover:text-foreground transition-colors">
                      Agent Runtime (FSM)
                    </Link>
                  </li>
                  <li>
                    <Link href="/product#sandboxing" className="hover:text-foreground transition-colors">
                      Security Sandbox
                    </Link>
                  </li>
                  <li>
                    <Link href="/product#bounded-recovery" className="hover:text-foreground transition-colors">
                      Bounded Error Recovery
                    </Link>
                  </li>
                </ul>
              </div>

              {/* Workspace Navigation */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground">
                  Platform
                </h4>
                <ul className="space-y-1.5 text-xs">
                  <li>
                    <Link href="/sessions" className="hover:text-foreground transition-colors">
                      Live Session Workspace
                    </Link>
                  </li>
                  <li>
                    <Link href="/repo" className="hover:text-foreground transition-colors">
                      Repository Explorer
                    </Link>
                  </li>
                  <li>
                    <Link href="/eval" className="hover:text-foreground transition-colors">
                      Evaluation Lab
                    </Link>
                  </li>
                  <li>
                    <Link href="/docs" className="hover:text-foreground transition-colors">
                      Documentation and CLI
                    </Link>
                  </li>
                  <li>
                    <Link href="/product" className="hover:text-foreground transition-colors">
                      System Architecture
                    </Link>
                  </li>
                </ul>
              </div>

              {/* Academic Attribution & Policies */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground">
                  Academic Project
                </h4>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Final-year project for CSE4192 (Machine Learning Projects with Python), designed for reproducible coding agent benchmarks.
                </p>
                <div className="pt-2 flex flex-col space-y-1 text-xs">
                  <Link href="/privacy" className="hover:text-foreground transition-colors">
                    Privacy Policy
                  </Link>
                  <Link href="/terms" className="hover:text-foreground transition-colors">
                    Terms of Service
                  </Link>
                </div>
              </div>
            </div>

            {/* Bottom Bar */}
            <div className="pt-6 border-t border-white/[0.06] flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px]">
              <div>
                <span>&copy; {new Date().getFullYear()} DevPilot Project. All rights reserved.</span>
              </div>
              <div className="flex items-center space-x-4">
                <span>Standardized on Python 3.11/3.12 and Next.js 15</span>
                <span className="text-violet-400 font-mono">MIT License</span>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
