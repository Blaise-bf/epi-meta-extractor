"use client";

import { memo, useMemo } from "react";
import { useAppStore } from "@/store/useAppStore";

export const ExtractionProgress = memo(function ExtractionProgress() {
  const progress = useAppStore((s) => s.progress);

  const percentage = useMemo(
    () => (progress.total > 0 ? (progress.processed / progress.total) * 100 : 0),
    [progress.processed, progress.total]
  );

  if (progress.total === 0) return null;

  return (
    <section className="surface-card rounded-2xl p-5 sm:p-6 mt-6">
      <div className="flex justify-between items-center text-sm text-slate-700 dark:text-slate-300 mb-2">
        <span className="font-medium">
          {progress.processed} / {progress.total} files processed
        </span>
        <span className="font-semibold text-cyan-700 dark:text-cyan-300">
          {percentage.toFixed(0)}%
        </span>
      </div>

      <div className="w-full bg-slate-200 dark:bg-slate-700 h-3 rounded-full overflow-hidden">
        <div
          className="bg-linear-to-r from-cyan-600 to-teal-500 h-3 rounded-full transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>

      {progress.currentArticle && (
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-3">
          Processing: {progress.currentArticle}
        </p>
      )}
    </section>
  );
});
