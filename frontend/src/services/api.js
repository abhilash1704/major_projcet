import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Interceptors can be added here in future sprints for JWT Auth
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // Global error handling
    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const systemService = {
  getHealth: () => apiClient.get('/health'),
  getStatus: () => apiClient.get('/status'),
  getVersion: () => apiClient.get('/version'),
  getInfo: () => apiClient.get('/system/info'),
};
