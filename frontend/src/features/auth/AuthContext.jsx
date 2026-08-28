import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authService } from './authService';

const AuthContext = createContext(null);

const DEFAULT_GUEST_USER = {
  name: 'AlgoRoutes User',
  full_name: 'AlgoRoutes User',
  email: 'user@algoroutes.io',
  provider: 'local',
  auth_provider: 'local',
  status: 'active',
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(DEFAULT_GUEST_USER);
  const [isAuthenticated, setIsAuthenticated] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  // Helper to load current user or restore session
  const initAuthSession = useCallback(async () => {
    try {
      const token = localStorage.getItem('rf_access_token');
      if (token) {
        const res = await authService.getCurrentUser();
        if (res && res.authenticated && res.user) {
          setUser(res.user);
          setIsAuthenticated(true);
        }
      }
    } catch {
      setUser(DEFAULT_GUEST_USER);
      setIsAuthenticated(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshSessionInternal = async () => {
    try {
      const res = await authService.refreshSession();
      if (res && res.authenticated && res.user) {
        setUser(res.user);
        setIsAuthenticated(true);
      } else {
        setUser(null);
        setIsAuthenticated(false);
      }
    } catch {
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  useEffect(() => {
    initAuthSession();
  }, [initAuthSession]);

  const login = async (email, password) => {
    setIsLoading(true);
    try {
      const res = await authService.login({ email, password });
      if (res && res.authenticated && res.user) {
        setUser(res.user);
        setIsAuthenticated(true);
        return { success: true, user: res.user };
      }
      return { success: false, message: res.message || 'Login failed' };
    } catch (err) {
      const msg = err.response?.data?.message || 'Failed to sign in. Please check your credentials.';
      return { success: false, message: msg };
    } finally {
      setIsLoading(false);
    }
  };

  const register = async ({ name, email, password, confirmPassword }) => {
    setIsLoading(true);
    try {
      const res = await authService.register({ name, email, password, confirmPassword });
      if (res && res.authenticated && res.user) {
        setUser(res.user);
        setIsAuthenticated(true);
        return { success: true, user: res.user };
      }
      return { success: false, message: res.message || 'Registration failed' };
    } catch (err) {
      const msg = err.response?.data?.message || 'Failed to create account. Please try again.';
      return { success: false, message: msg };
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setIsAuthenticated(false);
      setIsLoading(false);
    }
  };

  const forgotPassword = async (email) => {
    try {
      const res = await authService.forgotPassword(email);
      return { success: true, message: res.message };
    } catch (err) {
      const msg = err.response?.data?.message || 'Failed to request password reset.';
      return { success: false, message: msg };
    }
  };

  const resetPassword = async ({ token, password, confirmPassword }) => {
    try {
      const res = await authService.resetPassword({ token, password, confirmPassword });
      return { success: true, message: res.message };
    } catch (err) {
      const msg = err.response?.data?.message || 'Failed to reset password.';
      return { success: false, message: msg };
    }
  };

  const setDirectAuthSession = (userData, accessToken, refreshToken) => {
    authService.setSessionTokens(accessToken, refreshToken);
    setUser(userData);
    setIsAuthenticated(true);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoading,
        login,
        register,
        logout,
        refreshSession: refreshSessionInternal,
        getCurrentUser: initAuthSession,
        forgotPassword,
        resetPassword,
        setDirectAuthSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
