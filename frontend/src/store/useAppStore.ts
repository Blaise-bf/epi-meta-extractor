import { create } from "zustand";
import { EffectType, ExtractionProgressType } from "@/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MetaAnalysis {
  meta_analysis_id: string;
  title: string;
  details?: string;
  outcome?: string;
  exposure?: string;
  population?: string;
  comparison?: string;
  study_design?: string;
  created_at?: string;
  study_count?: number;
}

export interface AuthUser {
  id: string;
  email: string;
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
  };
  methods?: {
    study_design?: string;
    population?: string;
    sample_size?: number;
  };
  analysis?: {
    exposure?: string;
    outcome?: string;
    effect_measure?: string;
    effect_value?: number;
    ci_lower?: number;
    ci_upper?: number;
  };
  uploaded_at?: string;
  processing_time_ms?: number;
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

interface AppState {
  // Auth
  authUser: AuthUser | null;
  accessToken: string | null;
  authChecked: boolean;

  // Project
  effectType: EffectType | null;
  metaAnalysis: MetaAnalysis | null;

  // Studies
  studies: Study[];

  // Progress
  progress: ExtractionProgressType;

  // Global loading
  loading: boolean;
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

interface AppActions {
  setAuth: (user: AuthUser, token: string) => void;
  clearAuth: () => void;
  setAuthChecked: (checked: boolean) => void;

  setEffectType: (type: EffectType) => void;
  setMetaAnalysis: (ma: MetaAnalysis) => void;
  clearMetaAnalysis: () => void;

  setStudies: (studies: Study[]) => void;
  addStudy: (study: Study) => void;
  clearStudies: () => void;

  setProgress: (progress: ExtractionProgressType) => void;
  setLoading: (loading: boolean) => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAppStore = create<AppState & AppActions>((set) => ({
  // Initial state
  authUser: null,
  accessToken: null,
  authChecked: false,
  effectType: null,
  metaAnalysis: null,
  studies: [],
  progress: { processed: 0, total: 0 },
  loading: false,

  // Actions
  setAuth: (user, token) => set({ authUser: user, accessToken: token }),
  clearAuth: () => set({ authUser: null, accessToken: null }),
  setAuthChecked: (checked) => set({ authChecked: checked }),

  setEffectType: (type) => set({ effectType: type }),
  setMetaAnalysis: (ma) => set({ metaAnalysis: ma }),
  clearMetaAnalysis: () => set({ metaAnalysis: null }),

  setStudies: (studies) => set({ studies }),
  addStudy: (study) =>
    set((state) => ({ studies: [study, ...state.studies] })),
  clearStudies: () => set({ studies: [] }),

  setProgress: (progress) => set({ progress }),
  setLoading: (loading) => set({ loading }),
}));

// ---------------------------------------------------------------------------
// Selectors (use these in components to prevent unnecessary re-renders)
// ---------------------------------------------------------------------------

export const selectAuth = (state: AppState & AppActions) => ({
  authUser: state.authUser,
  accessToken: state.accessToken,
  authChecked: state.authChecked,
});

export const selectIsAuthenticated = (state: AppState & AppActions) =>
  !!state.accessToken;

export const selectMetaAnalysis = (state: AppState & AppActions) =>
  state.metaAnalysis;

export const selectEffectType = (state: AppState & AppActions) =>
  state.effectType;

export const selectStudies = (state: AppState & AppActions) => state.studies;

export const selectProgress = (state: AppState & AppActions) => state.progress;

export const selectLoading = (state: AppState & AppActions) => state.loading;
