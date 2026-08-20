import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach stored access token
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

export const authService = {
  async register({ name, email, password, confirmPassword }) {
    const response = await api.post('/auth/register', {
      full_name: name,
      email,
      password,
      confirm_password: confirmPassword,
    });
    if (response.data.access_token) {
      localStorage.setItem('rf_access_token', response.data.access_token);
    }
    if (response.data.refresh_token) {
      localStorage.setItem('rf_refresh_token', response.data.refresh_token);
    }
    return response.data;
  },

  async login({ email, password }) {
    const response = await api.post('/auth/login', { email, password });
    if (response.data.access_token) {
      localStorage.setItem('rf_access_token', response.data.access_token);
    }
    if (response.data.refresh_token) {
      localStorage.setItem('rf_refresh_token', response.data.refresh_token);
    }
    return response.data;
  },

  async logout() {
    try {
      const refreshToken = localStorage.getItem('rf_refresh_token');
      await api.post('/auth/logout', { refresh_token: refreshToken });
    } catch {
      // Ignore network errors on logout
    } finally {
      localStorage.removeItem('rf_access_token');
      localStorage.removeItem('rf_refresh_token');
    }
  },

  async refreshSession() {
    const refreshToken = localStorage.getItem('rf_refresh_token');
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken });
    if (response.data.access_token) {
      localStorage.setItem('rf_access_token', response.data.access_token);
    }
    if (response.data.refresh_token) {
      localStorage.setItem('rf_refresh_token', response.data.refresh_token);
    }
    return response.data;
  },

  async getCurrentUser() {
    const response = await api.get('/auth/me');
    return response.data;
  },

  async forgotPassword(email) {
    const response = await api.post('/auth/forgot-password', { email });
    return response.data;
  },

  async resetPassword({ token, password, confirmPassword }) {
    const response = await api.post('/auth/reset-password', {
      token,
      password,
      confirm_password: confirmPassword,
    });
    return response.data;
  },

  async handleGoogleCallback(code) {
    const response = await api.get(`/auth/google/callback?code=${code}`, {
      headers: { Accept: 'application/json' },
    });
    if (response.data.access_token) {
      localStorage.setItem('rf_access_token', response.data.access_token);
    }
    if (response.data.refresh_token) {
      localStorage.setItem('rf_refresh_token', response.data.refresh_token);
    }
    return response.data;
  },

  getGoogleAuthUrl() {
    return `${API_BASE_URL}/auth/google`;
  },

  setSessionTokens(accessToken, refreshToken) {
    if (accessToken) localStorage.setItem('rf_access_token', accessToken);
    if (refreshToken) localStorage.setItem('rf_refresh_token', refreshToken);
  }
};
