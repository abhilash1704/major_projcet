import axios from 'axios';

const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:5000';

const api = axios.create({
  baseURL: `${BACKEND_BASE_URL}/api`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('rf_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const historyService = {
  getHistory: async (params = {}) => {
    const response = await api.get('/history', { params });
    return response.data;
  },
  deleteHistory: async (id) => {
    const response = await api.delete(`/history/${id}`);
    return response.data;
  }
};
