/**
 * routeRequest.test.js — Stale Response & Request Cancellation Tests
 */
import test from "node:test";
import assert from "node:assert/strict";

import { createSequenceTracker } from "../services/apiStateMachine.js";

test("SequenceTracker correctly handles out-of-order responses (Stale Response Protection)", async () => {
  const tracker = createSequenceTracker();

  // Request 1: JP Nagar
  const seq1 = tracker.next();
  assert.equal(seq1, 1);

  // User changes mind quickly and selects Request 2: Whitefield
  const seq2 = tracker.next();
  assert.equal(seq2, 2);

  // Request 2 completes first (fast cache or closer route)
  const req2Response = { route: "Whitefield", seq: seq2 };
  assert.equal(tracker.isCurrent(req2Response.seq), true);

  // Request 1 completes later (slow network or long calculation)
  const req1Response = { route: "JP Nagar", seq: seq1 };
  assert.equal(tracker.isCurrent(req1Response.seq), false);

  // Verification: Request 1 MUST be discarded, leaving Request 2 active
  let activeRoute = null;
  if (tracker.isCurrent(req2Response.seq)) {
    activeRoute = req2Response.route;
  }
  if (tracker.isCurrent(req1Response.seq)) {
    activeRoute = req1Response.route; // should NOT execute
  }

  assert.equal(activeRoute, "Whitefield");
});

test("SequenceTracker increments monotonically on rapid route requests", () => {
  const tracker = createSequenceTracker();
  const seqs = [tracker.next(), tracker.next(), tracker.next(), tracker.next()];
  assert.deepEqual(seqs, [1, 2, 3, 4]);
  assert.equal(tracker.getCurrent(), 4);
  assert.equal(tracker.isCurrent(4), true);
  assert.equal(tracker.isCurrent(3), false);
});
