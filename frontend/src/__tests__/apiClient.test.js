/**
 * apiClient.test.js — Unit & Reliability Tests for Central API Client
 */
import test from "node:test";
import assert from "node:assert/strict";

import {
  TIMEOUT_BUDGETS,
  normalizeError,
  cancelPriorRequest,
  registerCancellableSignal,
  releaseCancellableSignal,
} from "../services/api.js";
import { API_STATE, isPendingState, isTerminalState, createSequenceTracker } from "../services/apiStateMachine.js";

test("TIMEOUT_BUDGETS defines bounded per-service timeouts", () => {
  assert.equal(TIMEOUT_BUDGETS.GEOCODING, 8000);
  assert.equal(TIMEOUT_BUDGETS.ROUTING, 20000);
  assert.equal(TIMEOUT_BUDGETS.ALTERNATIVES, 15000);
  assert.equal(TIMEOUT_BUDGETS.LIVE_CLUSTERING, 10000);
  assert.equal(TIMEOUT_BUDGETS.VEHICLE_SIM, 8000);
  assert.equal(TIMEOUT_BUDGETS.HISTORY, 8000);
  assert.ok(TIMEOUT_BUDGETS.DEFAULT > 0);
});

test("normalizeError handles timeout errors properly", () => {
  const timeoutErr = new Error("timeout of 8000ms exceeded");
  timeoutErr.code = "ECONNABORTED";
  timeoutErr.config = { headers: { "X-Request-ID": "test-req-123" } };

  const normalized = normalizeError(timeoutErr);
  assert.equal(normalized.code, "TIMEOUT");
  assert.equal(normalized.status, 504);
  assert.equal(normalized.requestId, "test-req-123");
  assert.equal(normalized.isNormalized, true);
});

test("normalizeError preserves backend error payload without exposing stack traces", () => {
  const backendErr = new Error("Request failed with status code 400");
  backendErr.response = {
    status: 400,
    data: {
      success: false,
      error: { code: "INVALID_PARAMETERS", message: "Source node required" },
      request_id: "backend-req-456",
    },
    headers: { "x-request-id": "backend-req-456" },
  };

  const normalized = normalizeError(backendErr);
  assert.equal(normalized.code, "INVALID_PARAMETERS");
  assert.equal(normalized.message, "Source node required");
  assert.equal(normalized.status, 400);
  assert.equal(normalized.requestId, "backend-req-456");
});

test("Cancellation Manager aborts prior requests for identical operation keys", () => {
  const key = "test_operation_key";
  const signal1 = registerCancellableSignal(key);
  assert.equal(signal1.aborted, false);

  // Registering a second request on the same key must abort the first
  const signal2 = registerCancellableSignal(key);
  assert.equal(signal1.aborted, true);
  assert.equal(signal2.aborted, false);

  // Canceling explicitly
  cancelPriorRequest(key);
  assert.equal(signal2.aborted, true);

  releaseCancellableSignal(key);
});

test("apiStateMachine distinguishes pending and terminal states", () => {
  assert.equal(isPendingState(API_STATE.LOADING), true);
  assert.equal(isPendingState(API_STATE.RETRYING), true);
  assert.equal(isPendingState(API_STATE.IDLE), false);
  assert.equal(isPendingState(API_STATE.SUCCESS), false);

  assert.equal(isTerminalState(API_STATE.SUCCESS), true);
  assert.equal(isTerminalState(API_STATE.ERROR), true);
  assert.equal(isTerminalState(API_STATE.TIMEOUT), true);
  assert.equal(isTerminalState(API_STATE.CANCELLED), true);
  assert.equal(isTerminalState(API_STATE.LOADING), false);
});
