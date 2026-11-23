import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "DevPilot — Autonomous Coding Agent Harness",
  description: "Repository-aware adaptive context retrieval and bounded recovery agent harness for IEEE publication.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background font-sans antialiased text-foreground flex flex-col justify-between">
        <div>
          <Navbar />
          <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">{children}</main>
        </div>
        <footer className="border-t border-border py-4 text-center text-xs text-muted-foreground">
          DevPilot: Adaptive Hybrid Retrieval & Structured Recovery Harness • B.Tech Final Year IEEE Project
        </footer>
      </body>
    </html>
  );
}
