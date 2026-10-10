import axios from "axios";
import { useAuthStore } from "@/store/authStore";

// ─────────────────────────────────────────────────────────────────────────────
// Axios instance — all requests go through this
// Base URL is handled by Vite proxy: /api → http://localhost:8000/api
// ─────────────────────────────────────────────────────────────────────────────
const apiClient = axios.create({
  baseURL: "/",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

// ── Request Interceptor: Attach JWT token automatically ───────────────────────
apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: Auto-logout on 401 Unauthorized ────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default apiClient;
