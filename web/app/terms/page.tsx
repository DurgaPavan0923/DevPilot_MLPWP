import React from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function TermsOfServicePage() {
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
          Terms of Service
        </h1>
        <p className="text-xs text-muted-foreground">
          Last updated: November 2026
        </p>
      </div>

      <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-muted-foreground leading-relaxed">
        <strong className="text-foreground">Notice:</strong> These terms describe terms of use for the DevPilot research software prototype and should be reviewed by project owners before public deployment.
      </div>

      <div className="space-y-6 text-xs text-muted-foreground leading-relaxed">
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-foreground">1. Academic Purpose and License</h2>
          <p>
            DevPilot is an open-source academic research harness licensed under the Apache License 2.0.
            It is developed for academic evaluation in course CSE4192 (Machine Learning Projects with Python) by Ayusman Das, Selina Mohanty, Rajana Durga Pavan Kumar, and Akanshaa Mohanta under faculty advisor Jagseer Singh.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-foreground">2. Code Modification and Execution Disclaimer</h2>
          <p>
            DevPilot automates code retrieval, file editing, shell command execution, and test execution.
            While sandbox isolation and path jails are provided, users are solely responsible for providing adequate container boundaries and reviewing code modifications before deploying generated patches to production systems.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-foreground">3. Upstream LLM Costs and Limits</h2>
          <p>
            Inference fees charged by upstream LLM providers (including OpenAI, Anthropic, Google, and DeepSeek) are the sole responsibility of the user providing the API credentials.
            Users should configure budget limits in DevPilot (<code className="rounded bg-muted px-1 font-mono text-foreground">max_cost_usd</code> and <code className="rounded bg-muted px-1 font-mono text-foreground">max_steps</code>) to prevent unintended token expenditures.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-foreground">4. No Warranty</h2>
          <p>
            The software is provided &quot;as is&quot;, without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.
            In no event shall the authors or copyright holders be liable for any claim, damages, or other liability arising from the use of this software.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-foreground">5. Inquiries</h2>
          <p>
            Questions regarding terms of use can be addressed to the project team at{" "}
            <a href={`mailto:${contactEmail}`} className="text-primary hover:underline font-mono">
              {contactEmail}
            </a>.
          </p>
        </section>
      </div>
    </div>
  );
}
