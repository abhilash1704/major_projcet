/**
 * vehicleService.js — Vehicle Simulation API Service
 * Routes all requests through the central apiClient.
 */
import { apiClient, TIMEOUT_BUDGETS } from "./api";

const API_PREFIX = "/api/vehicles";

export const getVehicles = async () => {
  const response = await apiClient.get(API_PREFIX, { timeout: TIMEOUT_BUDGETS.VEHICLE_SIM });
  return response.data;
};

export const getVehicle = async (vehicleId) => {
  const response = await apiClient.get(`${API_PREFIX}/${vehicleId}`, { timeout: TIMEOUT_BUDGETS.VEHICLE_SIM });
  return response.data.vehicle;
};

export const createVehicle = async (data) => {
  const response = await apiClient.post(API_PREFIX, data, { timeout: TIMEOUT_BUDGETS.VEHICLE_SIM });
  return response.data.vehicle;
};

export const updateVehicle = async (vehicleId, data) => {
  const response = await apiClient.put(`${API_PREFIX}/${vehicleId}`, data, { timeout: TIMEOUT_BUDGETS.VEHICLE_SIM });
  return response.data.vehicle;
};

export const deleteVehicle = async (vehicleId) => {
  const response = await apiClient.delete(`${API_PREFIX}/${vehicleId}`, { timeout: TIMEOUT_BUDGETS.VEHICLE_SIM });
  return response.data;
};

export const generateVehicles = async (count, seed = null) => {
  const payload = { count };
  if (seed !== null) payload.seed = seed;
  const response = await apiClient.post(`${API_PREFIX}/generate`, payload, { timeout: 20000 });
  return response.data;
};

export const clearSimulation = async () => {
  const response = await apiClient.delete(`${API_PREFIX}/simulation`, { timeout: TIMEOUT_BUDGETS.VEHICLE_SIM });
  return response.data;
};

export const startSimulation = async () => {
  const response = await apiClient.post(`${API_PREFIX}/simulation/start`, {}, { timeout: TIMEOUT_BUDGETS.VEHICLE_SIM });
  return response.data;
};

export const pauseSimulation = async () => {
  const response = await apiClient.post(`${API_PREFIX}/simulation/pause`, {}, { timeout: TIMEOUT_BUDGETS.VEHICLE_SIM });
  return response.data;
};

export const resumeSimulation = async () => {
  const response = await apiClient.post(`${API_PREFIX}/simulation/resume`, {}, { timeout: TIMEOUT_BUDGETS.VEHICLE_SIM });
  return response.data;
};

export const updateSimulation = async (deltaSeconds, seed = null) => {
  const payload = { delta_seconds: deltaSeconds };
  if (seed !== null) payload.seed = seed;
  const response = await apiClient.post(`${API_PREFIX}/simulation/update`, payload, { timeout: 20000 });
  return response.data;
};

export const getSnapshot = async () => {
  const response = await apiClient.get(`${API_PREFIX}/snapshot`, { timeout: TIMEOUT_BUDGETS.VEHICLE_SIM });
  return response.data;
};

export const vehicleService = {
  getVehicles,
  getVehicle,
  createVehicle,
  updateVehicle,
  deleteVehicle,
  generateVehicles,
  clearSimulation,
  startSimulation,
  pauseSimulation,
  resumeSimulation,
  updateSimulation,
  getSnapshot,
};
