export type EffectType = "RR" | "OR" | "HR" | "MD" | "SMD";

export interface ExtractionProgressType {
  processed: number;
  total: number;
  currentArticle?: string;
}
