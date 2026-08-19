import axios from "axios";
import { useAuthStore } from "@/stores/auth-store";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;

export const authApi = {
  login: (email: string, password: string) =>
    api.post("/api/v1/auth/login", { email, password }),
  register: (data: any) => api.post("/api/v1/auth/register", data),
  me: () => api.get("/api/v1/auth/me"),
};

export const profileApi = {
  list: (params?: any) => api.get("/api/v1/profiles", { params }),
  get: (id: string) => api.get(`/api/v1/profiles/${id}`),
  create: (data: any) => api.post("/api/v1/profiles", data),
  update: (id: string, data: any) => api.put(`/api/v1/profiles/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/profiles/${id}`),
};

export const photoshootApi = {
  list: (params?: any) => api.get("/api/v1/photoshoots", { params }),
  get: (id: string) => api.get(`/api/v1/photoshoots/${id}`),
  create: (data: any) => api.post("/api/v1/photoshoots", data),
};

export const analysisApi = {
  list: (params?: any) => api.get("/api/v1/analyses", { params }),
  get: (id: string) => api.get(`/api/v1/analyses/${id}`),
  start: (photoshootId: string, data: any) =>
    api.post(`/api/v1/ai/analyze?photoshoot_id=${photoshootId}`, data),
};

export const visagismApi = {
  analyzeUpload: (file: File, angle = "front") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("angle", angle);
    return api.post("/api/v1/ai/analyze/visagism/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

export const reportApi = {
  list: (params?: any) => api.get("/api/v1/reports", { params }),
  get: (id: string) => api.get(`/api/v1/reports/${id}`),
  create: (data: any) => api.post("/api/v1/reports", data),
  generatePdf: (id: string) => api.post(`/api/v1/reports/${id}/generate-pdf`),
};
