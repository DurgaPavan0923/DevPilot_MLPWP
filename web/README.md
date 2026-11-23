# DevPilot Web Dashboard

The `web/` directory hosts the DevPilot interactive web application—a modern Next.js 15 (App Router) user interface that provides real-time telemetry, live execution event streaming, interactive AST code inspection, side-by-side Monaco diff viewing, and an Evaluation Research Lab.

---

## 1. Features & Capabilities

- **Real-Time Agent Telemetry (`/` & `/sessions/[id]`)**:
  Connects to DevPilot's FastAPI backend via Server-Sent Events (SSE). Streams the live ReAct reasoning cycle (`ANALYZE` -> `RETRIEVE` -> `PLAN` -> `EXECUTE` -> `RECOVER` -> `VERIFY` -> `DONE`) with step-by-step token counters, duration timers, and tool execution logs.

- **Interactive Monaco Code Diff Viewer**:
  Provides a side-by-side visual diff editor (powered by `@monaco-editor/react`) displaying before/after code modifications made by the agent before committing or verifying patches.

- **AST Dependency & Symbol Graph (`/repo`)**:
  Visualizes parsed repository functions, classes, imports, and call relationships extracted by the Tree-sitter and NetworkX analysis engines.

- **Evaluation & Hypothesis Testing Lab (`/eval`)**:
  Presents comparative benchmark evaluations across the three agent configurations (`Basic`, `Fixed-RAG`, `Full DevPilot`). Dynamically exports camera-ready IEEE LaTeX tables and CSV datasets, and renders McNemar $p$-values and bootstrap confidence intervals.

- **Offline Demonstration Mode**:
  Includes standalone mock fixtures (`lib/mock-data.ts`) allowing the frontend to be fully demonstrated and tested offline without requiring active LLM provider keys or running local backend processes.

---

## 2. Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Framework** | Next.js 15.1 (App Router), React 19 |
| **Language** | TypeScript (Strict mode enabled) |
| **Styling** | Tailwind CSS, Lucide React icons |
| **Editors & Visuals** | `@monaco-editor/react` (Monaco Diff Editor), SVG Data Visualizations |
| **State & Communication** | Native Server-Sent Events (`EventSource`), Fetch API |
| **Package Manager** | `pnpm` (Workspace-ready lockfile) |

---

## 3. Directory Layout

```
web/
├── app/
│   ├── layout.tsx         # Root layout with navigation sidebar and health badge
│   ├── page.tsx           # Dashboard home: active sessions, token metrics, cost ledger
│   ├── repo/page.tsx      # Repository explorer, AST symbol tree, and dependency graph
│   ├── eval/page.tsx      # Comparative evaluation lab & statistical analysis viewer
│   └── sessions/[id]/     # Live session trace viewer, event logs, and Monaco diff view
├── components/            # Reusable UI widgets, diff viewer, status pills, and charts
├── lib/
│   ├── api.ts             # Strongly typed API client connecting to FastAPI backend
│   ├── mock-data.ts       # Realistic offline demo fixtures and simulated event streams
│   └── utils.ts           # String formatters, currency helpers, and Tailwind utilities
├── tests/
│   └── frontend.test.ts   # Node test runner suite verifying mock schemas and data contracts
├── package.json           # Scripts and dependencies
└── tsconfig.json          # Strict TypeScript compiler options
```

---

## 4. Development Workflow

Ensure Node.js 20+ and `pnpm` are installed:

```bash
# Navigate to web directory
cd web

# 1. Install dependencies
pnpm install

# 2. Run local development server (starts on http://localhost:3000)
pnpm dev

# 3. Validate TypeScript type safety
pnpm typecheck

# 4. Check linting rules
pnpm lint

# 5. Run frontend unit tests
pnpm test

# 6. Build optimized production bundle
pnpm build
```

---

## 5. Docker Deployment

The web dashboard is containerized via `docker/Dockerfile.web` using a lightweight multi-stage Alpine build:

```bash
# Build standalone web container
docker build -t devpilot-web -f docker/Dockerfile.web web/

# Run containerized UI on port 3000
docker run -d -p 3000:3000 --name devpilot-web devpilot-web
```
