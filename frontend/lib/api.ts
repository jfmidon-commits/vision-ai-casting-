import axios from "axios";
import { useAuthStore } from "@/stores/auth-store";

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://vision-ai-casting-api.onrender.com";

const api = axios.create({
  baseURL: apiBaseUrl,
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
  async (error) => {
    const config = error.config as (typeof error.config & { __retryCount?: number }) | undefined;
    const status = error.response?.status as number | undefined;
    const method = config?.method?.toLowerCase();
    const isTransientGetFailure =
      method === "get" &&
      (!error.response || status === 429 || status === 502 || status === 503 || status === 504);

    if (config && isTransientGetFailure) {
      config.__retryCount = (config.__retryCount || 0) + 1;
      if (config.__retryCount <= 12) {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        return api.request(config);
      }
    }

    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }

    if (!error.response) {
      error.response = {
        data: {
          message: `Falha de rede ao acessar ${apiBaseUrl}: ${error.message || "sem resposta do servidor"}`,
        },
      };
    } else if (!error.response.data?.detail && !error.response.data?.message) {
      error.response.data = {
        ...(typeof error.response.data === "object" && error.response.data ? error.response.data : {}),
        message: `Falha HTTP ${error.response.status || "desconhecida"} em ${error.config?.url || "requisição da API"}`,
      };
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
  uploadPhoto: (photoshootId: string, file: File, angle: string) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post(`/api/v1/photoshoots/${photoshootId}/photos`, formData, {
      params: { angle },
    });
  },
};

export const photoApi = {
  get: (id: string) => api.get(`/api/v1/photos/${id}`),
  triage: (id: string) => api.post(`/api/v1/photos/${id}/triage`),
};

export const analysisApi = {
  list: (params?: any) => api.get("/api/v1/analyses", { params }),
  get: (id: string) => api.get(`/api/v1/analyses/${id}`),
  getVisagism: (id: string) => api.get(`/api/v1/analyses/${id}/visagism`),
  start: (photoshootId: string, data: any) =>
    api.post(`/api/v1/ai/analyze?photoshoot_id=${photoshootId}`, data),
  simulateVisagism: (id: string, haircutName: string) =>
    api.post(`/api/v1/analyses/${id}/visagism/simulate`, {
      haircut_name: haircutName,
    }),
};

export const reportApi = {
  list: (params?: any) => api.get("/api/v1/reports", { params }),
  get: (id: string) => api.get(`/api/v1/reports/${id}`),
  create: (data: any) => api.post("/api/v1/reports", data),
  generatePdf: (id: string) => api.post(`/api/v1/reports/${id}/generate-pdf`),
};