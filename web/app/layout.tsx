import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import Link from "next/link";

export const metadata: Metadata = {
  title: "DevPilot: Autonomous Coding Agent Harness",
  description:
    "A coding agent harness that retrieves repository context, runs tools in a sandbox, retries on errors with a bounded limit, and verifies changes with tests.",
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
      "A coding agent harness that retrieves repository context, runs tools in a sandbox, retries on errors with a bounded limit, and verifies changes with tests.",
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
    <html lang="en">
      <body className="min-h-screen bg-background font-sans antialiased text-foreground flex flex-col justify-between">
        <div>
          <Navbar />
          <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">{children}</main>
        </div>
        <footer className="border-t border-border bg-card/50 py-8 text-xs text-muted-foreground">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <p className="font-medium text-foreground">
                DevPilot: Repository-Aware Coding Agent Harness
              </p>
              <p className="mt-1">
                Academic project for CSE4192, Machine Learning Projects with Python.
              </p>
            </div>
            <div className="flex items-center space-x-6">
              <Link href="/privacy" className="hover:text-foreground transition-colors">
                Privacy Policy
              </Link>
              <Link href="/terms" className="hover:text-foreground transition-colors">
                Terms and Conditions
              </Link>
              <a
                href="https://github.com/DurgaPavan0923/DevPilot_MLPWP.git"
                target="_blank"
                rel="noreferrer"
                className="hover:text-foreground transition-colors"
              >
                GitHub Repository
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
