/**
 * vehicleService.js — Sprint 4.2
 *
 * Axios service for the Vehicle Simulation API.
 * Mirrors backend /api/vehicles endpoints.
 *
 * NOT connected to the map yet — UI integration is deferred to a future sprint.
 */
import axios from 'axios';

const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:5000';
const API = `${BACKEND_BASE_URL}/api/vehicles`;

// ── Helpers ────────────────────────────────────────────────────────────────────

function handleError(error) {
  if (error.response) {
    const data = error.response.data;
    const status = error.response.status;
    const detail = data?.message || data?.error || (typeof data === 'string' ? data : null);
    throw new Error(
      detail ? `Vehicle API Error: ${detail}` : `Vehicle API failed with status code ${status}`
    );
  } else if (error.request) {
    throw new Error('Vehicle simulation backend timeout or unreachable. Please check backend connection and database locks.');
  }
  throw new Error(error.message || 'Unknown vehicle service error.');
}

// ── Read ───────────────────────────────────────────────────────────────────────

/**
 * Retrieve all vehicle records.
 * @returns {Promise<{vehicles: Array, count: number}>}
 */
export const getVehicles = async () => {
  try {
    const response = await axios.get(API, { timeout: 8000 });
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Retrieve a single vehicle by ID.
 * @param {string} vehicleId
 * @returns {Promise<Object>} vehicle object
 */
export const getVehicle = async (vehicleId) => {
  try {
    const response = await axios.get(`${API}/${vehicleId}`, { timeout: 8000 });
    return response.data.vehicle;
  } catch (error) {
    handleError(error);
  }
};

// ── Create ─────────────────────────────────────────────────────────────────────

/**
 * Create a single vehicle record.
 * @param {Object} data  latitude, longitude, speed, heading, current_node, current_edge, status
 * @returns {Promise<Object>} created vehicle object
 */
export const createVehicle = async (data) => {
  try {
    const response = await axios.post(API, data, { timeout: 8000 });
    return response.data.vehicle;
  } catch (error) {
    handleError(error);
  }
};

// ── Update ─────────────────────────────────────────────────────────────────────

/**
 * Update a vehicle's state.
 * @param {string} vehicleId
 * @param {Object} data  Partial vehicle fields to update.
 * @returns {Promise<Object>} updated vehicle object
 */
export const updateVehicle = async (vehicleId, data) => {
  try {
    const response = await axios.put(`${API}/${vehicleId}`, data, { timeout: 8000 });
    return response.data.vehicle;
  } catch (error) {
    handleError(error);
  }
};

// ── Delete ─────────────────────────────────────────────────────────────────────

/**
 * Delete a single vehicle record.
 * @param {string} vehicleId
 * @returns {Promise<Object>} confirmation message
 */
export const deleteVehicle = async (vehicleId) => {
  try {
    const response = await axios.delete(`${API}/${vehicleId}`, { timeout: 8000 });
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

// ── Generation ─────────────────────────────────────────────────────────────────

/**
 * Trigger vehicle generation on road network edges.
 * @param {number} count  Number of vehicles to generate (1 – 500).
 * @param {number|null} seed  Optional random seed for reproducibility.
 * @returns {Promise<{generated: number, failed: number, vehicles: Array}>}
 */
export const generateVehicles = async (count, seed = null) => {
  const payload = { count };
  if (seed !== null) payload.seed = seed;

  try {
    const response = await axios.post(`${API}/generate`, payload, { timeout: 30000 });
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

// ── Simulation reset ───────────────────────────────────────────────────────────

/**
 * Clear all simulated vehicles from the database.
 * Does NOT affect users, road graph, or authentication.
 * @returns {Promise<{deleted: number}>}
 */
export const clearSimulation = async () => {
  try {
    const response = await axios.delete(`${API}/simulation`, { timeout: 8000 });
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

// ── Simulation Update (Sprint 4.3 / 6.5) ──────────────────────────────────────────────

/**
 * Start the simulation session.
 * @returns {Promise<Object>}
 */
export const startSimulation = async () => {
  try {
    const response = await axios.post(`${API}/simulation/start`, {}, { timeout: 8000 });
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Pause the simulation session.
 * @returns {Promise<Object>}
 */
export const pauseSimulation = async () => {
  try {
    const response = await axios.post(`${API}/simulation/pause`, {}, { timeout: 8000 });
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Resume the simulation session.
 * @returns {Promise<Object>}
 */
export const resumeSimulation = async () => {
  try {
    const response = await axios.post(`${API}/simulation/resume`, {}, { timeout: 8000 });
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Advance all active vehicles by deltaSeconds.
 * @param {number} deltaSeconds
 * @param {number|null} seed Optional RNG seed for deterministic edge transitions
 * @returns {Promise<{vehicles_moved: number, vehicles_stopped: number, vehicles: Array}>}
 */
export const updateSimulation = async (deltaSeconds, seed = null) => {
  const payload = { delta_seconds: deltaSeconds };
  if (seed !== null) payload.seed = seed;

  try {
    const response = await axios.post(`${API}/simulation/update`, payload, { timeout: 30000 });
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Lightweight endpoint returning all vehicle positions.
 * @returns {Promise<{count: number, vehicles: Array}>}
 */
export const getSnapshot = async () => {
  try {
    const response = await axios.get(`${API}/snapshot`, { timeout: 8000 });
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

// Default named export for convenience
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
