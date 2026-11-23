import {
  MOCK_SESSIONS,
  MOCK_EVENT_STREAM,
  MOCK_DIFF_ORIGINAL,
  MOCK_DIFF_MODIFIED,
  MOCK_RETRIEVED_CHUNKS,
  MOCK_EVAL_SUMMARY,
  type MockSession,
  type MockAgentEvent,
} from "./mock-data";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function isMockMode(): boolean {
  if (typeof window !== "undefined") {
    const override = localStorage.getItem("devpilot_mock_mode");
    if (override !== null) return override === "true";
  }
  return process.env.NEXT_PUBLIC_MOCK_API === "true";
}

export function setMockMode(enabled: boolean): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("devpilot_mock_mode", enabled ? "true" : "false");
    window.dispatchEvent(new Event("storage"));
  }
}

export async function fetchHealth(): Promise<{ status: string; version: string; providers: string[] }> {
  if (isMockMode()) {
    return { status: "healthy", version: "0.1.0-mock", providers: ["openai", "anthropic", "gemini", "deepseek", "ollama", "mock"] };
  }
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error("Backend unavailable");
    const data = await res.json();
    return {
      status: data.status,
      version: data.version,
      providers: data.registered_providers || [],
    };
  } catch {
    return { status: "degraded", version: "offline", providers: ["mock"] };
  }
}

export async function fetchSessions(): Promise<MockSession[]> {
  if (isMockMode()) {
    return MOCK_SESSIONS;
  }
  try {
    const res = await fetch(`${API_BASE}/api/sessions`);
    if (!res.ok) throw new Error("Failed to fetch sessions");
    const data = await res.json();
    return data.sessions.map((s: any) => ({
      id: s.id,
      status: s.status,
      preset: s.preset,
      provider: s.provider,
      model: s.model,
      created_at: s.created_at,
      steps: s.steps,
      total_tokens: s.total_tokens,
      total_cost_usd: s.total_cost_usd,
      task: s.metadata?.task || "Code repair task",
    }));
  } catch {
    return MOCK_SESSIONS;
  }
}

export async function createSession(params: {
  preset: string;
  provider: string;
  model: string;
  task: string;
  permission_mode: string;
}): Promise<{ id: string }> {
  if (isMockMode()) {
    const id = `sess_local_${Date.now().toString(36)}`;
    return { id };
  }
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      preset: params.preset,
      provider: params.provider,
      model: params.model,
      task: params.task,
      permission_mode: params.permission_mode,
    }),
  });
  if (!res.ok) throw new Error("Failed to create session");
  const data = await res.json();
  return { id: data.session.id };
}

export async function fetchSessionDiff(sessionId: string): Promise<{ original: string; modified: string }> {
  if (isMockMode()) {
    return { original: MOCK_DIFF_ORIGINAL, modified: MOCK_DIFF_MODIFIED };
  }
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/diff`);
    if (!res.ok) throw new Error("Failed to fetch diff");
    const data = await res.json();
    return { original: data.diff ? "" : MOCK_DIFF_ORIGINAL, modified: data.diff || MOCK_DIFF_MODIFIED };
  } catch {
    return { original: MOCK_DIFF_ORIGINAL, modified: MOCK_DIFF_MODIFIED };
  }
}

export async function fetchEvalReport(): Promise<typeof MOCK_EVAL_SUMMARY> {
  return MOCK_EVAL_SUMMARY;
}
