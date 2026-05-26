import axios from 'axios';
import { useAuthStore } from '@/stores/auth';

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

request.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore();
    const token = authStore.accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const authStore = useAuthStore();
    if (error.response?.status === 401) {
      authStore.logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default request;