export type EffectType = "RR" | "OR" | "HR" | "MD" | "SMD" | "PROPORTION";

export interface ExtractionProgressType {
  processed: number;
  total: number;
  currentArticle?: string;
}
