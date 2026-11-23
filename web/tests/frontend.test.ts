import test from "node:test";
import assert from "node:assert/strict";
import {
  MOCK_SESSIONS,
  MOCK_EVENT_STREAM,
  MOCK_EVAL_SUMMARY,
} from "../lib/mock-data.ts";

test("Mock fixtures integrity and schema conformance", () => {
  assert.ok(Array.isArray(MOCK_SESSIONS));
  assert.ok(MOCK_SESSIONS.length >= 4);

  const sample = MOCK_SESSIONS[0];
  assert.ok(sample.id);
  assert.ok(sample.status);
  assert.ok(sample.preset);
  assert.equal(typeof sample.total_tokens, "number");
  assert.equal(typeof sample.total_cost_usd, "number");
});

test("Mock SSE event sequence conforms to AgentEventType lifecycle", () => {
  assert.ok(Array.isArray(MOCK_EVENT_STREAM));
  const eventTypes = MOCK_EVENT_STREAM.map((e) => e.type);

  assert.ok(eventTypes.includes("STATE_CHANGE"));
  assert.ok(eventTypes.includes("THOUGHT"));
  assert.ok(eventTypes.includes("TOOL_CALL"));
  assert.ok(eventTypes.includes("TOOL_RESULT"));
  assert.ok(eventTypes.includes("FINAL"));
});

test("Evaluation benchmark results contain valid statistical results", () => {
  assert.ok(MOCK_EVAL_SUMMARY.presets.length === 3);
  const full = MOCK_EVAL_SUMMARY.presets[0];
  assert.ok(full.resolve_rate > 0.8);

  const stat = MOCK_EVAL_SUMMARY.statistical_significance;
  assert.ok(stat.p_value < 0.05);
  assert.equal(stat.is_significant, true);
  assert.ok(Array.isArray(stat.bootstrap_ci_95));
});
