/**
 * api.js — Centralized Resilient HTTP Client for RouteFlow
 *
 * Implements:
 *   1. Configurable per-service timeout budgets (geocoding, routing, alternatives, clustering, etc.)
 *   2. Request correlation with unique X-Request-ID propagation
 *   3. Bounded exponential backoff retries with jitter for transient errors (502, 503, 504, 429, network failures)
 *   4. Strict non-retry of client errors (400, 401, 403, 404, validation errors)
 *   5. Centralized auth token injection & 401 refresh/redirect handling
 *   6. Operation-scoped AbortController cancellation pool
 *   7. Standardized error normalization: { success: false, error: { code, message }, status, requestId }
 */
import axios from "axios";

export const BACKEND_BASE_URL =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_BACKEND_URL) ||
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) ||
  (typeof process !== "undefined" && process.env?.VITE_BACKEND_URL) ||
  "http://127.0.0.1:5000";

export const TIMEOUT_BUDGETS = Object.freeze({
  GEOCODING:       8000,
  ROUTING:         20000,
  ALTERNATIVES:    15000,
  LIVE_CLUSTERING: 10000,
  VEHICLE_SIM:     8000,
  HISTORY:         8000,
  AUTH:            10000,
  DEFAULT:         10000,
});

// ── In-Flight Cancellation Registry ──────────────────────────────────────────
const cancellationRegistry = new Map(); // operationKey -> AbortController

export function cancelPriorRequest(operationKey) {
  if (!operationKey) return;
  const existing = cancellationRegistry.get(operationKey);
  if (existing) {
    existing.abort();
    cancellationRegistry.delete(operationKey);
  }
}

export function registerCancellableSignal(operationKey) {
  if (!operationKey) return undefined;
  cancelPriorRequest(operationKey);
  const controller = new AbortController();
  cancellationRegistry.set(operationKey, controller);
  return controller.signal;
}

export function releaseCancellableSignal(operationKey) {
  if (operationKey) {
    cancellationRegistry.delete(operationKey);
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function generateRequestId() {
  const rand = Math.random().toString(36).substring(2, 10);
  return `rf_req_${Date.now().toString(36)}_${rand}`;
}

function calculateBackoffDelay(attempt, baseDelay = 400, maxDelay = 3000) {
  const exponential = baseDelay * Math.pow(2, attempt);
  const jitter = Math.random() * 200;
  return Math.min(maxDelay, exponential + jitter);
}

function isTransientError(error) {
  // Network connection error / no response
  if (!error.response) {
    return true;
  }
  const status = error.response.status;
  // 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout, 429 Too Many Requests
  if (status === 502 || status === 503 || status === 504 || status === 429) {
    return true;
  }
  return false;
}

// ── Axios Instance Creation ──────────────────────────────────────────────────
export const apiClient = axios.create({
  baseURL: BACKEND_BASE_URL,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  timeout: TIMEOUT_BUDGETS.DEFAULT,
  withCredentials: true,
});

// ── Request Interceptor ──────────────────────────────────────────────────────
apiClient.interceptors.request.use(
  (config) => {
    // 1. Correlation ID
    if (!config.headers["X-Request-ID"]) {
      config.headers["X-Request-ID"] = config.requestId || generateRequestId();
    }

    // 2. Idempotency Key forwarding
    if (config.idempotencyKey && !config.headers["Idempotency-Key"]) {
      config.headers["Idempotency-Key"] = config.idempotencyKey;
    }

    // 3. Auth Token
    const token = localStorage.getItem("rf_access_token");
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 4. Operation cancellation
    if (config.operationKey && !config.signal) {
      config.signal = registerCancellableSignal(config.operationKey);
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response & Retry Interceptor ─────────────────────────────────────────────
let isRefreshing = false;
let refreshSubscribers = [];

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

apiClient.interceptors.response.use(
  (response) => {
    if (response.config?.operationKey) {
      releaseCancellableSignal(response.config.operationKey);
    }
    return response;
  },
  async (error) => {
    const originalConfig = error.config || {};
    if (originalConfig.operationKey) {
      releaseCancellableSignal(originalConfig.operationKey);
    }

    // 1. Handle Request Cancellation
    if (axios.isCancel(error) || error.name === "CanceledError" || error.name === "AbortError") {
      const cancelError = new DOMException("Request was cancelled.", "AbortError");
      cancelError.isCancelled = true;
      return Promise.reject(cancelError);
    }

    // 2. Handle 401 Unauthorized (Token Refresh Flow)
    if (error.response?.status === 401 && !originalConfig._isAuthRetry) {
      const refreshToken = localStorage.getItem("rf_refresh_token");
      if (refreshToken && !originalConfig.url?.includes("/auth/")) {
        if (!isRefreshing) {
          isRefreshing = true;
          try {
            const refreshRes = await axios.post(
              `${BACKEND_BASE_URL}/api/auth/refresh`,
              { refresh_token: refreshToken },
              { timeout: TIMEOUT_BUDGETS.AUTH }
            );

            const newAccess = refreshRes.data?.access_token;
            if (newAccess) {
              localStorage.setItem("rf_access_token", newAccess);
              if (refreshRes.data?.refresh_token) {
                localStorage.setItem("rf_refresh_token", refreshRes.data.refresh_token);
              }
              onRefreshed(newAccess);
              isRefreshing = false;
              originalConfig._isAuthRetry = true;
              originalConfig.headers.Authorization = `Bearer ${newAccess}`;
              return apiClient(originalConfig);
            }
          } catch (refreshErr) {
            isRefreshing = false;
            refreshSubscribers = [];
            localStorage.removeItem("rf_access_token");
            localStorage.removeItem("rf_refresh_token");
            if (typeof window !== "undefined" && window.location.pathname !== "/login" && window.location.pathname !== "/") {
              window.location.href = "/login?expired=1";
            }
            return Promise.reject(normalizeError(refreshErr));
          }
        } else {
          // Queue request until refresh completes
          return new Promise((resolve, reject) => {
            subscribeTokenRefresh((newToken) => {
              if (newToken) {
                originalConfig._isAuthRetry = true;
                originalConfig.headers.Authorization = `Bearer ${newToken}`;
                resolve(apiClient(originalConfig));
              } else {
                reject(error);
              }
            });
          });
        }
      }
    }

    // 3. Transient Error Bounded Retry Policy
    const maxRetries = originalConfig.maxRetries ?? (originalConfig.retryTransient !== false ? 2 : 0);
    const retryCount = originalConfig._retryCount || 0;

    if (retryCount < maxRetries && isTransientError(error)) {
      originalConfig._retryCount = retryCount + 1;
      const delayMs = calculateBackoffDelay(retryCount);
      console.warn(
        `[apiClient] Transient failure (${error.response?.status || error.code}). Retrying attempt ${originalConfig._retryCount}/${maxRetries} in ${Math.round(delayMs)}ms...`
      );
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      return apiClient(originalConfig);
    }

    // 4. Normalize and reject
    return Promise.reject(normalizeError(error));
  }
);

// ── Error Normalization ──────────────────────────────────────────────────────
export function normalizeError(error) {
  if (error.isNormalized) return error;

  const status = error.response?.status || (error.code === "ECONNABORTED" ? 504 : 0);
  const data = error.response?.data;
  const reqId = error.config?.headers?.["X-Request-ID"] || error.response?.headers?.["x-request-id"] || "unknown";

  let code = "NETWORK_ERROR";
  let message = "Network communication failed. Please check your connection.";

  if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
    code = "TIMEOUT";
    message = "The request timed out. Please try again.";
  } else if (status === 404) {
    code = "NOT_FOUND";
    message = data?.message || data?.error || "The requested resource was not found.";
  } else if (status === 400) {
    code = "VALIDATION_ERROR";
    message = data?.message || data?.error || "Invalid request parameters.";
  } else if (status === 401) {
    code = "UNAUTHORIZED";
    message = "Your session has expired. Please sign in again.";
  } else if (status === 403) {
    code = "FORBIDDEN";
    message = "You do not have permission to perform this action.";
  } else if (status === 429) {
    code = "RATE_LIMITED";
    message = "Too many requests. Please wait a moment before trying again.";
  } else if (status >= 500) {
    code = "SERVER_ERROR";
    message = data?.message || data?.error || "Server temporarily unavailable. Please try again.";
  } else if (typeof data === "string" && data.trim()) {
    message = data;
  }

  // Backend structured error override
  if (data && typeof data === "object") {
    if (data.error && typeof data.error === "object") {
      if (data.error.code) code = data.error.code;
      if (data.error.message) message = data.error.message;
    } else if (typeof data.error === "string") {
      message = data.error;
    }
    if (data.code) code = data.code;
    if (data.message && typeof data.message === "string") message = data.message;
  }

  const normalized = new Error(message);
  normalized.name = "ApiError";
  normalized.code = code;
  normalized.status = status;
  normalized.requestId = reqId;
  normalized.details = data?.errors || data?.details || null;
  normalized.data = data;
  normalized.isNormalized = true;
  normalized.originalError = error;

  return normalized;
}

// ── System Service ───────────────────────────────────────────────────────────
export const systemService = {
  getHealth: () => apiClient.get("/api/health"),
  getStatus: () => apiClient.get("/api/v1/status"),
  getVersion: () => apiClient.get("/api/v1/version"),
  getInfo: () => apiClient.get("/api/v1/system/info"),
};

export default apiClient;
