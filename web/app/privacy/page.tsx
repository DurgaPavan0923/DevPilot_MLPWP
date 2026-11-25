import React from "react";
import Link from "next/link";
import { Shield, ArrowLeft } from "lucide-react";

export default function PrivacyPolicyPage() {
  const contactEmail = process.env.NEXT_PUBLIC_CONTACT_EMAIL || "durgapavan0923@gmail.com";

  return (
    <div className="max-w-3xl space-y-8 pb-12">
      <div className="border-b border-border pb-6 space-y-2">
        <Link
          href="/"
          className="inline-flex items-center space-x-1.5 text-xs text-muted-foreground hover:text-foreground transition"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Home</span>
        </Link>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Privacy Policy
        </h1>
        <p className="text-xs text-muted-foreground">
          Last updated: November 2026
        </p>
      </div>

      <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-muted-foreground leading-relaxed">
        <strong className="text-foreground">Notice:</strong> These documents describe the technical data practices of the DevPilot research prototype and should be reviewed by project owners before public deployment.
      </div>

      <div className="space-y-6 text-xs text-muted-foreground leading-relaxed">
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-foreground">1. Academic Context</h2>
          <p>
            DevPilot is an academic capstone research project developed for course CSE4192 (Machine Learning Projects with Python) under the instruction of Jagseer Singh.
            The project team members are Ayusman Das (Registration 2341004073), Selina Mohanty (Registration 2341013299), Rajana Durga Pavan Kumar (Registration 2341011099), and Akanshaa Mohanta (Registration 2341013229).
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-foreground">2. Data Storage and Session Persistence</h2>
          <p>
            DevPilot stores session execution logs, event traces, tool outputs, and cost metrics locally in an SQLite database (<code className="rounded bg-muted px-1 font-mono text-foreground">sessions.db</code>) managed by the backend server.
            No persistent user tracking profiles or third-party telemetry databases are utilized.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-foreground">3. API Credentials and Secret Management</h2>
          <p>
            LLM provider credentials (such as OpenAI, Anthropic, Gemini, or DeepSeek API keys) are configured server-side through environment variables or local <code className="rounded bg-muted px-1 font-mono text-foreground">.env</code> files.
            API keys are never returned in client API responses, never logged to terminal standard output, and never transmitted to third parties other than the respective upstream LLM provider endpoint.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-foreground">4. Upstream LLM Data Transmission</h2>
          <p>
            When an agent session is launched, task instructions and relevant source code snippets retrieved from the target repository are transmitted to the selected LLM provider (such as Anthropic, OpenAI, or Google) solely to generate reasoning hypotheses and code edits.
            Users should verify that repository contents comply with their organization data governance policies before dispatching queries to external cloud APIs.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-foreground">5. Cookies and Web Analytics</h2>
          <p>
            The DevPilot web interface does not use tracking cookies, marketing pixels, or third-party behavioral analytics.
            Client-side preferences (such as mock mode toggle and UI theme preference) are stored solely in browser LocalStorage.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-foreground">6. Contact Information</h2>
          <p>
            For inquiries regarding this research prototype or its data handling practices, contact the maintainers at{" "}
            <a href={`mailto:${contactEmail}`} className="text-primary hover:underline font-mono">
              {contactEmail}
            </a>.
          </p>
        </section>
      </div>
    </div>
  );
}
