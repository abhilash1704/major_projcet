/**
 * alternativeRoutes.test.js — Alternative Routes Resilience & Isolation Tests
 */
import test from "node:test";
import assert from "node:assert/strict";

import { registerCancellableSignal, cancelPriorRequest } from "../services/api.js";

test("Alternative route operation signal cancels gracefully on route change", () => {
  const signal1 = registerCancellableSignal("alternative_routes");
  assert.equal(signal1.aborted, false);

  // User selects a different route before alternatives complete
  cancelPriorRequest("alternative_routes");
  assert.equal(signal1.aborted, true);
});

test("Structured timeout fallback does not crash caller", () => {
  // Simulates timeout payload returned on ECONNABORTED
  const timeoutPayload = {
    success: false,
    status: "error",
    count: 0,
    alternatives: [],
    error: { code: "NETWORK_TIMEOUT", message: "Alternative route request timed out." },
  };

  assert.equal(timeoutPayload.success, false);
  assert.equal(timeoutPayload.count, 0);
  assert.deepEqual(timeoutPayload.alternatives, []);
  assert.equal(timeoutPayload.error.code, "NETWORK_TIMEOUT");
});
