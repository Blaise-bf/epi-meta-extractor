"use client";

import { memo, useCallback } from "react";
import { EffectType } from "@/types";
import { useAppStore, selectEffectType } from "@/store/useAppStore";

const effects: EffectType[] = ["RR", "OR", "HR", "MD", "SMD", "PROPORTION"];
const descriptions: Record<EffectType, string> = {
  RR: "Risk Ratio",
  OR: "Odds Ratio",
  HR: "Hazard Ratio",
  MD: "Mean Difference",
  SMD: "Std. Mean Diff.",
  PROPORTION: "Proportion",
};

const EffectButton = memo(function EffectButton({
  effect,
  isSelected,
  onSelect,
}: {
  effect: EffectType;
  isSelected: boolean;
  onSelect: (effect: EffectType) => void;
}) {
  return (
    <button
      onClick={() => onSelect(effect)}
      className={`border rounded-2xl p-3 text-left transition ${
        isSelected
          ? "bg-gradient-to-br from-cyan-600 to-teal-600 text-white border-transparent shadow"
          : "bg-white/90 dark:bg-slate-900/70 text-slate-900 dark:text-slate-100 border-slate-200 dark:border-slate-700 hover:border-cyan-300 dark:hover:border-cyan-700 hover:bg-cyan-50/50 dark:hover:bg-slate-800"
      }`}
    >
      <div className="text-base font-semibold">{effect}</div>
      <div
        className={`text-xs mt-1 ${
          isSelected ? "text-cyan-50" : "text-slate-500 dark:text-slate-400"
        }`}
      >
        {descriptions[effect]}
      </div>
    </button>
  );
});

export const EffectSelector = memo(function EffectSelector() {
  const effectType = useAppStore(selectEffectType);
  const setEffectType = useAppStore((state) => state.setEffectType);

  const handleSelect = useCallback(
    (effect: EffectType) => setEffectType(effect),
    [setEffectType]
  );

  return (
    <section className="surface-card rounded-2xl p-5 sm:p-6 space-y-4">
      <div>
        <h2 className="text-lg sm:text-xl font-semibold text-slate-900 dark:text-slate-100">
          Select Effect Type
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Choose the measurement model for extraction and synthesis.
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {effects.map((effect) => (
          <EffectButton
            key={effect}
            effect={effect}
            isSelected={effectType === effect}
            onSelect={handleSelect}
          />
        ))}
      </div>
    </section>
  );
});
