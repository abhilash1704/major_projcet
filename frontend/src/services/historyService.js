/**
 * historyService.js — Route History Service
 * Utilizes the central apiClient for correlation, token management, and timeout control.
 */
import { apiClient, TIMEOUT_BUDGETS } from "./api";

export const historyService = {
  getHistory: async (params = {}, signal = null) => {
    const response = await apiClient.get("/api/history", {
      params,
      timeout: TIMEOUT_BUDGETS.HISTORY,
      signal: signal || undefined,
    });
    return response.data;
  },
  deleteHistory: async (id) => {
    const response = await apiClient.delete(`/api/history/${id}`, {
      timeout: TIMEOUT_BUDGETS.HISTORY,
    });
    return response.data;
  },
};
