import axios, { InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { env } from '../config/env';

export const apiClient = axios.create({
  baseURL: env.API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Automatically inject Bearer Token into outbound requests
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('cortex_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Centralized error interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle session expiry / token invalidation
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Emit event or clear storage to redirect user to login
      localStorage.removeItem('cortex_token');
      window.dispatchEvent(new Event('auth_expired'));
    }

    return Promise.reject(error);
  }
);