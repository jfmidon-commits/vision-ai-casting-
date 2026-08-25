import axios from "axios";
import { useAuthStore } from "@/stores/auth-store";

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://vision-ai-casting-api.onrender.com";

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
});

const MAX_GET_RETRIES = 12;
const RETRY_DELAYS = [2000, 3000, 5000, 8000, 13000];

type RetryConfig = {
  __retryCount?: number;
  __requestStartTime?: number;
  __operation?: string;
};

function isTransientStatus(status?: number) {
  return status === 429 || status === 502 || status === 503 || status === 504;
}

function operationConfig(operation: string, extra: Record<string, unknown> = {}) {
  return { ...extra, __operation: operation } as any;
}

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  (config as typeof config & RetryConfig).__requestStartTime = Date.now();
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config as (typeof error.config & RetryConfig) | undefined;
    const status = error.response?.status as number | undefined;
    const method = config?.method?.toLowerCase() || "";
    const isTransientGetFailure =
      method === "get" && (!error.response || isTransientStatus(status));

    if (config && isTransientGetFailure) {
      config.__retryCount = (config.__retryCount || 0) + 1;
      if (config.__retryCount <= MAX_GET_RETRIES) {
        const delay = RETRY_DELAYS[Math.min(config.__retryCount - 1, RETRY_DELAYS.length - 1)];
        console.warn(
          `[API retry] ${config.__operation || method.toUpperCase()} ${config.url} ` +
            `tentativa ${config.__retryCount}/${MAX_GET_RETRIES} em ${delay}ms`
        );
        await new Promise((resolve) => setTimeout(resolve, delay));
        return api.request(config);
      }
    }

    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }

    const elapsed = config?.__requestStartTime
      ? Date.now() - config.__requestStartTime
      : undefined;
    const operation = config?.__operation || `${method.toUpperCase() || "REQUEST"} ${config?.url || "API"}`;
    const elapsedLabel = elapsed !== undefined ? ` após ${elapsed}ms` : "";

    if (!error.response) {
      error.response = {
        data: {
          message: `Falha de rede em ${operation} ao acessar ${apiBaseUrl}: ${error.message || "sem resposta do servidor"}${elapsedLabel}`,
        },
      };
    } else if (!error.response.data?.detail && !error.response.data?.message) {
      error.response.data = {
        ...(typeof error.response.data === "object" && error.response.data ? error.response.data : {}),
        message: `Falha HTTP ${error.response.status || "desconhecida"} em ${operation}${elapsedLabel}`,
      };
    }

    return Promise.reject(error);
  }
);

export default api;

export const authApi = {
  login: (email: string, password: string) =>
    api.post("/api/v1/auth/login", { email, password }, operationConfig("login")),
  register: (data: any) => api.post("/api/v1/auth/register", data, operationConfig("cadastro")),
  me: () => api.get("/api/v1/auth/me", operationConfig("validar sessão")),
};

export const profileApi = {
  list: (params?: any) => api.get("/api/v1/profiles", operationConfig("carregar perfis", { params })),
  get: (id: string) => api.get(`/api/v1/profiles/${id}`, operationConfig("carregar perfil")),
  create: (data: any) => api.post("/api/v1/profiles", data, operationConfig("criar perfil")),
  update: (id: string, data: any) => api.put(`/api/v1/profiles/${id}`, data, operationConfig("atualizar perfil")),
  delete: (id: string) => api.delete(`/api/v1/profiles/${id}`, operationConfig("excluir perfil")),
};

export const photoshootApi = {
  list: (params?: any) => api.get("/api/v1/photoshoots", operationConfig("listar sessões de fotos", { params })),
  get: (id: string) => api.get(`/api/v1/photoshoots/${id}`, operationConfig("carregar sessão de fotos")),
  create: (data: any) => api.post("/api/v1/photoshoots", data, operationConfig("criar sessão de fotos")),
  uploadPhoto: (photoshootId: string, file: File, angle: string) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post(
      `/api/v1/photoshoots/${photoshootId}/photos`,
      formData,
      operationConfig(`upload da foto ${angle}`, {
        params: { angle },
        timeout: 60000,
      })
    );
  },
};

export const photoApi = {
  get: (id: string) => api.get(`/api/v1/photos/${id}`, operationConfig("carregar foto")),
  triage: (id: string) => api.post(`/api/v1/photos/${id}/triage`, undefined, operationConfig(`triagem da foto ${id.slice(0, 8)}`)),
};

export const analysisApi = {
  list: (params?: any) => api.get("/api/v1/analyses", operationConfig("listar análises", { params })),
  get: (id: string) => api.get(`/api/v1/ai/status/${id}`, operationConfig(`polling da análise ${id.slice(0, 8)}`)),
  getVisagism: (id: string) => api.get(`/api/v1/analyses/${id}/visagism`, operationConfig(`carregar resultado ${id.slice(0, 8)}`)),
  start: (photoshootId: string, data: any) =>
    api.post(
      `/api/v1/ai/analyze?photoshoot_id=${photoshootId}`,
      data,
      operationConfig("iniciar análise")
    ),
  simulateVisagism: (id: string, haircutName: string) =>
    api.post(
      `/api/v1/analyses/${id}/visagism/simulate`,
      { haircut_name: haircutName },
      operationConfig("simular visagismo")
    ),
};

export const reportApi = {
  list: (params?: any) => api.get("/api/v1/reports", operationConfig("listar relatórios", { params })),
  get: (id: string) => api.get(`/api/v1/reports/${id}`, operationConfig("carregar relatório")),
  create: (data: any) => api.post("/api/v1/reports", data, operationConfig("criar relatório")),
  generatePdf: (id: string) => api.post(`/api/v1/reports/${id}/generate-pdf`, undefined, operationConfig("gerar PDF")),
};
