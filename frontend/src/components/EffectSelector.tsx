"use client";

import { EffectType } from "@/types";
import { useAppStore } from "@/store/useAppStore";

const effects: EffectType[] = ["RR", "OR", "HR", "MD", "SMD"];

export const EffectSelector = () => {
  const { effectType, setEffectType } = useAppStore();

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-medium text-slate-900 dark:text-slate-100">Select Effect Type</h2>

      <div className="grid grid-cols-2 gap-3">
        {effects.map((effect) => (
          <button
            key={effect}
            onClick={() => setEffectType(effect)}
            className={`border rounded-2xl p-3 text-sm transition ${
                effectType === effect
                  ? "bg-blue-600 dark:bg-blue-500 text-white border-blue-600 dark:border-blue-500"
                  : "bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700"
              }
            `}
          >
            {effect}
          </button>
        ))}
      </div>
    </div>
  );
};
