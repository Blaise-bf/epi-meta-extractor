import { create } from "zustand";
import { EffectType, ExtractionProgressType } from "@/types";

interface MetaAnalysis {
  meta_analysis_id: string;
  title: string;
  details?: string;
  outcome?: string;
  exposure?: string;
  created_at?: string;
  study_count?: number;
}

interface AuthUser {
  id: string;
  email: string;
}

interface Study {
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

interface AppState {
  authUser: AuthUser | null;
  accessToken: string | null;
  setAuth: (user: AuthUser, token: string) => void;
  clearAuth: () => void;
  authChecked: boolean;
  setAuthChecked: (checked: boolean) => void;

  effectType: EffectType | null;
  setEffectType: (type: EffectType) => void;

  metaAnalysis: MetaAnalysis | null;
  setMetaAnalysis: (ma: MetaAnalysis) => void;
  clearMetaAnalysis: () => void;

  progress: ExtractionProgressType;
  setProgress: (progress: ExtractionProgressType) => void;

  studies: Study[];
  setStudies: (studies: Study[]) => void;
  addStudy: (study: Study) => void;
  clearStudies: () => void;

  loading: boolean;
  setLoading: (loading: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  authUser: null,
  accessToken: null,
  setAuth: (user, token) => set({ authUser: user, accessToken: token }),
  clearAuth: () => set({ authUser: null, accessToken: null }),
  authChecked: false,
  setAuthChecked: (checked) => set({ authChecked: checked }),

  effectType: null,
  setEffectType: (type) => set({ effectType: type }),

  metaAnalysis: null,
  setMetaAnalysis: (ma) => set({ metaAnalysis: ma }),
  clearMetaAnalysis: () => set({ metaAnalysis: null }),

  progress: { processed: 0, total: 0 },
  setProgress: (progress) => set({ progress }),

  studies: [],
  setStudies: (studies) => set({ studies }),
  addStudy: (study) => set((state) => ({ studies: [study, ...state.studies] })),
  clearStudies: () => set({ studies: [] }),

  loading: false,
  setLoading: (loading) => set({ loading }),
}));
