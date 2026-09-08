/**
 * apiStateMachine.js — Standard API States & Sequence Protection
 *
 * Provides a standardized 8-state machine for asynchronous frontend operations:
 * IDLE, LOADING, SUCCESS, EMPTY, RETRYING, TIMEOUT, ERROR, CANCELLED.
 *
 * Also provides sequence/generation ID tracking to discard stale out-of-order responses
 * (e.g. Request 1 finishing after Request 2).
 */

export const API_STATE = Object.freeze({
  IDLE:      "IDLE",
  LOADING:   "LOADING",
  SUCCESS:   "SUCCESS",
  EMPTY:     "EMPTY",
  RETRYING:  "RETRYING",
  TIMEOUT:   "TIMEOUT",
  ERROR:     "ERROR",
  CANCELLED: "CANCELLED",
});

export const isPendingState = (state) =>
  state === API_STATE.LOADING || state === API_STATE.RETRYING;

export const isTerminalState = (state) =>
  state === API_STATE.SUCCESS ||
  state === API_STATE.EMPTY ||
  state === API_STATE.TIMEOUT ||
  state === API_STATE.ERROR ||
  state === API_STATE.CANCELLED;

/**
 * Creates a thread-safe / render-safe sequence tracker.
 * Usage:
 *   const tracker = createSequenceTracker();
 *   const seq = tracker.next();
 *   ...
 *   if (!tracker.isCurrent(seq)) return; // discard stale response
 */
export function createSequenceTracker(initialSeq = 0) {
  let currentSeq = initialSeq;

  return {
    next() {
      currentSeq += 1;
      return currentSeq;
    },
    getCurrent() {
      return currentSeq;
    },
    isCurrent(seq) {
      return seq === currentSeq;
    },
    reset() {
      currentSeq = 0;
    },
  };
}
