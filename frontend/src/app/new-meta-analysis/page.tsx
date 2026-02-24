"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/store/useAppStore";
import { API_BASE_URL, buildAuthHeaders } from "@/lib/api";

export default function NewMetaAnalysisPage() {
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [outcome, setOutcome] = useState("");
  const [exposure, setExposure] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const { setMetaAnalysis, accessToken, authChecked } = useAppStore();

  useEffect(() => {
    if (authChecked && !accessToken) {
      router.push("/auth");
    }
  }, [accessToken, authChecked, router]);

  const handleCreate = async (e: React.FormEvent) => {
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
      const response = await axios.post(`${API_BASE_URL}/meta-analyses`, null, {
        params: {
          title: title.trim(),
          details: details.trim(),
          outcome: outcome.trim(),
          exposure: exposure.trim(),
        },
        headers: buildAuthHeaders(accessToken),
      });

      const { meta_analysis_id, created_at } = response.data;

      // Store in Zustand
      setMetaAnalysis({
        meta_analysis_id,
        title: title.trim(),
        details: details.trim() || undefined,
        outcome: outcome.trim(),
        exposure: exposure.trim(),
        created_at,
      });

      // Redirect to home page for uploading
      router.push("/");
    } catch (err) {
      console.error("Failed to create meta-analysis:", err);
      setError("Failed to create meta-analysis. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">New Meta-Analysis</h1>
          <p className="text-gray-600 mb-8">
            Create a new meta-analysis project to organize and extract data from multiple studies.
          </p>

          <form onSubmit={handleCreate} className="space-y-6">
            {/* Title Field */}
            <div>
              <label htmlFor="title" className="block text-sm font-semibold text-gray-700 mb-2">
                Meta-Analysis Title <span className="text-red-500">*</span>
              </label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Cardiovascular Risk Factors in Type 2 Diabetes"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
              <p className="text-xs text-gray-500 mt-1">
                This title will be used to identify your meta-analysis project.
              </p>
            </div>

            {/* Details Field */}
            <div>
              <label htmlFor="details" className="block text-sm font-semibold text-gray-700 mb-2">
                Research Details (Optional)
              </label>
              <textarea
                id="details"
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                placeholder="Add any relevant details, research notes, or specific instructions for extraction..."
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                disabled={loading}
              />
              <p className="text-xs text-gray-500 mt-1">
                This information will be stored with your meta-analysis for reference.
              </p>
            </div>

            {/* Outcome Field */}
            <div>
              <label htmlFor="outcome" className="block text-sm font-semibold text-gray-700 mb-2">
                Outcome Variable <span className="text-red-500">*</span>
              </label>
              <input
                id="outcome"
                type="text"
                value={outcome}
                onChange={(e) => setOutcome(e.target.value)}
                placeholder="e.g., lung cancer, cardiovascular disease, mortality"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
              <p className="text-xs text-gray-500 mt-1">
                The health outcome you're studying in your meta-analysis.
              </p>
            </div>

            {/* Exposure Field */}
            <div>
              <label htmlFor="exposure" className="block text-sm font-semibold text-gray-700 mb-2">
                Exposure Variable <span className="text-red-500">*</span>
              </label>
              <input
                id="exposure"
                type="text"
                value={exposure}
                onChange={(e) => setExposure(e.target.value)}
                placeholder="e.g., smoking, obesity, physical activity"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
              <p className="text-xs text-gray-500 mt-1">
                The exposure or risk factor you're studying.
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => router.back()}
                disabled={loading}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-400 font-medium transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !title.trim() || !outcome.trim() || !exposure.trim()}
                className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-semibold transition"
              >
                {loading ? "Creating..." : "Create Meta-Analysis"}
              </button>
            </div>
          </form>

          {/* Info Box */}
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">Next Steps:</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>✓ Create your meta-analysis project</li>
              <li>✓ Upload PDF files or ZIP archives</li>
              <li>✓ All studies will be grouped under this project</li>
              <li>✓ Download results as CSV or PDF anytime</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
