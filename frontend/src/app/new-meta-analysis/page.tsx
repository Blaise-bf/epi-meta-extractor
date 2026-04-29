"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/Skeleton";

export default function NewMetaAnalysisPage() {
  const router = useRouter();
  const accessToken = useAppStore((s) => s.accessToken);
  const authChecked = useAppStore((s) => s.authChecked);
  const setMetaAnalysis = useAppStore((s) => s.setMetaAnalysis);

  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [outcome, setOutcome] = useState("");
  const [exposure, setExposure] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authChecked && !accessToken) {
      router.push("/auth");
    }
  }, [accessToken, authChecked, router]);

  const handleCreate = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!title.trim()) {
        setError("Meta-analysis title is required");
        return;
      }
      if (!outcome.trim() || !exposure.trim()) {
        setError("Outcome and exposure variables are required");
        return;
      }
      if (!accessToken) {
        setError("Please sign in to create a meta-analysis.");
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const { data } = await api.metaAnalyses.create({
          title: title.trim(),
          details: details.trim(),
          outcome: outcome.trim(),
          exposure: exposure.trim(),
        });

        setMetaAnalysis({
          meta_analysis_id: data.meta_analysis_id,
          title: title.trim(),
          details: details.trim() || undefined,
          outcome: outcome.trim(),
          exposure: exposure.trim(),
          created_at: data.created_at,
        });

        router.push("/");
      } catch (err: any) {
        const msg =
          err?.response?.data?.detail ||
          err?.response?.data?.message ||
          "Failed to create meta-analysis. Please try again.";
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [title, details, outcome, exposure, accessToken, setMetaAnalysis, router]
  );

  return (
    <div className="min-h-screen bg-linear-to-br from-blue-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800 p-6">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            New Meta-Analysis
          </h1>
          <p className="text-gray-600 dark:text-gray-300 mb-8">
            Create a new meta-analysis project to organize and extract data from
            multiple studies.
          </p>

          <form onSubmit={handleCreate} className="space-y-6">
            <div>
              <label
                htmlFor="title"
                className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2"
              >
                Meta-Analysis Title <span className="text-red-500">*</span>
              </label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Cardiovascular Risk Factors in Type 2 Diabetes"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-700 dark:text-white"
                disabled={loading}
              />
            </div>

            <div>
              <label
                htmlFor="details"
                className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2"
              >
                Research Details (Optional)
              </label>
              <textarea
                id="details"
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                placeholder="Add any relevant details, research notes, or specific instructions for extraction..."
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none dark:bg-slate-700 dark:text-white"
                disabled={loading}
              />
            </div>

            <div>
              <label
                htmlFor="outcome"
                className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2"
              >
                Outcome Variable <span className="text-red-500">*</span>
              </label>
              <input
                id="outcome"
                type="text"
                value={outcome}
                onChange={(e) => setOutcome(e.target.value)}
                placeholder="e.g., lung cancer, cardiovascular disease, mortality"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-700 dark:text-white"
                disabled={loading}
              />
            </div>

            <div>
              <label
                htmlFor="exposure"
                className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2"
              >
                Exposure Variable <span className="text-red-500">*</span>
              </label>
              <input
                id="exposure"
                type="text"
                value={exposure}
                onChange={(e) => setExposure(e.target.value)}
                placeholder="e.g., smoking, obesity, physical activity"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-700 dark:text-white"
                disabled={loading}
              />
            </div>

            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <p className="text-red-700 dark:text-red-300 text-sm">{error}</p>
              </div>
            )}

            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => router.back()}
                disabled={loading}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50 font-medium transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !title.trim() || !outcome.trim() || !exposure.trim()}
                className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-semibold transition flex items-center justify-center gap-2"
              >
                {loading && <Spinner className="w-4 h-4" />}
                {loading ? "Creating..." : "Create Meta-Analysis"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
