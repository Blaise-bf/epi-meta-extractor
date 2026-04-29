"use client";

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from "axios";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Axios instance with interceptors
// ---------------------------------------------------------------------------

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor: attach auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== "undefined") {
      const token = window.localStorage.getItem("epi_access_token");
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 globally
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      window.localStorage.removeItem("epi_access_token");
      window.localStorage.removeItem("epi_user");
      if (!window.location.pathname.startsWith("/auth")) {
        window.location.href = "/auth";
      }
    }
    return Promise.reject(error);
  }
);

export { apiClient };

// ---------------------------------------------------------------------------
// Auth headers helper (for non-apiClient usage like FormData uploads)
// ---------------------------------------------------------------------------

export const buildAuthHeaders = (token?: string | null): Record<string, string> => {
  let authToken = token;
  if (!authToken && typeof window !== "undefined") {
    authToken = window.localStorage.getItem("epi_access_token");
  }
  if (!authToken) return {};
  return { Authorization: `Bearer ${authToken}` };
};

// ---------------------------------------------------------------------------
// Typed API helpers
// ---------------------------------------------------------------------------

export interface MetaAnalysis {
  meta_analysis_id: string;
  title: string;
  details?: string;
  outcome?: string;
  exposure?: string;
  created_at?: string;
  study_count?: number;
}

export interface Study {
  _id: string;
  filename: string;
  effect_type: string;
  meta_analysis_id?: string;
  metadata?: {
    title?: string;
    authors?: string;
    year?: number;
    journal?: string;
    study_id?: string;
    country?: string;
    continent?: string;
  };
  methods?: {
    study_design?: string;
    population?: string;
    sample_size?: number;
    exposure_definition?: string;
    outcome_definition?: string;
  };
  analysis?: {
    exposure?: string;
    outcome?: string;
    effect_measure?: string;
    effect_value?: number;
    ci_lower?: number;
    ci_upper?: number;
    p_value?: number;
    group_statistics?: {
      exposed?: { n?: number; mean?: number; sd?: number };
      control?: { n?: number; mean?: number; sd?: number };
    };
    // Effect-size-specific blocks
    proportion_data?: {
      events?: number;
      sample_size?: number;
      proportion?: number;
      se?: number;
      ci_lower?: number;
      ci_upper?: number;
    };
    two_by_two_table?: {
      a?: number;
      b?: number;
      c?: number;
      d?: number;
    };
    continuous_data?: {
      exposed_mean?: number;
      exposed_sd?: number;
      exposed_n?: number;
      control_mean?: number;
      control_sd?: number;
      control_n?: number;
    };
    survival_data?: {
      events_exposed?: number;
      events_control?: number;
      person_time_exposed?: number;
      person_time_control?: number;
      rate_exposed?: number;
      rate_control?: number;
    };
    adjustment_variables?: string[];
  };
  uploaded_at?: string;
  processing_time_ms?: number;
}

export interface BatchStatus {
  batch_id: string;
  status: string;
  processed_count: number;
  total_files: number;
  current_file?: string;
  success_count: number;
  failed_count: number;
}

export const api = {
  auth: {
    requestLink: (email: string) =>
      apiClient.post("/auth/request-link", { email }),
    verify: (token: string) =>
      apiClient.post("/auth/verify", { token }, { withCredentials: true }),
    refresh: () =>
      apiClient.post("/auth/refresh", {}, { withCredentials: true }),
    logout: () =>
      apiClient.post("/auth/logout", {}, { withCredentials: true }),
    me: () => apiClient.get("/auth/me"),
  },
  metaAnalyses: {
    list: () =>
      apiClient.get<{ meta_analyses: MetaAnalysis[] }>("/meta-analyses"),
    get: (id: string) => apiClient.get<MetaAnalysis>(`/meta-analyses/${id}`),
    create: (params: {
      title: string;
      details?: string;
      outcome?: string;
      exposure?: string;
    }) => apiClient.post("/meta-analyses", null, { params }),
    delete: (id: string) => apiClient.delete(`/meta-analyses/${id}`),
    getStudies: (id: string) =>
      apiClient.get<{ studies: Study[] }>(`/meta-analyses/${id}/studies`),
  },
  studies: {
    list: () => apiClient.get<{ studies: Study[] }>("/studies"),
    get: (id: string) => apiClient.get<Study>(`/studies/${id}`),
    byEffect: (effectType: string) =>
      apiClient.get<{ studies: Study[] }>(`/studies/effect/${effectType}`),
    exportCsv: () =>
      apiClient.get("/studies/export/csv", { responseType: "blob" }),
  },
  upload: (formData: FormData, params: URLSearchParams) =>
    apiClient.post("/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      params,
    }),
  batch: {
    getStatus: (batchId: string) =>
      apiClient.get<BatchStatus>(`/batch/${batchId}`),
  },
  search: (query: string, limit = 5) =>
    apiClient.post("/search", null, { params: { query, limit } }),
  health: () => apiClient.get("/health"),
  grobidHealth: () => apiClient.get("/health/grobid"),
};
