"use client";

import { useAppStore } from "@/store/useAppStore";

export const ExtractionProgress = () => {
  const { progress } = useAppStore();

  const percentage =
    progress.total > 0
      ? (progress.processed / progress.total) * 100
      : 0;

  return (
    <div className="mt-6">
      <div className="flex justify-between text-sm text-slate-700 dark:text-slate-300 mb-2">
        <span>
          {progress.processed} / {progress.total} processed
        </span>
        <span>{percentage.toFixed(0)}%</span>
      </div>

      <div className="w-full bg-slate-200 dark:bg-slate-700 h-3 rounded-full">
        <div
          className="bg-blue-600 dark:bg-blue-500 h-3 rounded-full transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>

      {progress.currentArticle && (
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
          Processing: {progress.currentArticle}
        </p>
      )}
    </div>
  );
};
