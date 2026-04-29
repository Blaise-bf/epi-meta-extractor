"use client";

import { memo, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/store/useAppStore";
import { api, type Study } from "@/lib/api";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { StudyCardSkeleton, Spinner } from "@/components/ui/Skeleton";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const StudyCard = memo(function StudyCard({ study }: { study: Study }) {
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-6 shadow-sm hover:shadow-md dark:hover:shadow-slate-900/20 transition">
      <div className="mb-4">
        <div className="flex justify-between items-start mb-2">
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex-1">
            {study.metadata?.title || study.filename}
          </h2>
          <span className="ml-4 px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 text-xs font-medium rounded">
            {study.effect_type}
          </span>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">{study.filename}</p>
      </div>

      {study.metadata && (
        <div className="mb-4 pb-4 border-b border-slate-200 dark:border-slate-700">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Metadata</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            {study.metadata.authors && (
              <div>
                <span className="text-slate-600 dark:text-slate-400">Authors:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">{study.metadata.authors}</p>
              </div>
            )}
            {study.metadata.year && (
              <div>
                <span className="text-slate-600 dark:text-slate-400">Year:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">{study.metadata.year}</p>
              </div>
            )}
            {study.metadata.journal && (
              <div className="col-span-2">
                <span className="text-slate-600 dark:text-slate-400">Journal:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">{study.metadata.journal}</p>
              </div>
            )}
            {(study.metadata.country || study.metadata.continent) && (
              <div className="col-span-2">
                <span className="text-slate-600 dark:text-slate-400">Location:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">
                  {[study.metadata.country, study.metadata.continent].filter(Boolean).join(" — ")}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {study.methods && (
        <div className="mb-4 pb-4 border-b border-slate-200 dark:border-slate-700">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Methods</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            {study.methods.study_design && (
              <div>
                <span className="text-slate-600 dark:text-slate-400">Design:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">{study.methods.study_design}</p>
              </div>
            )}
            {study.methods.sample_size && (
              <div>
                <span className="text-slate-600 dark:text-slate-400">Sample Size:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">{study.methods.sample_size.toLocaleString()}</p>
              </div>
            )}
            {study.methods.population && (
              <div className="col-span-2">
                <span className="text-slate-600 dark:text-slate-400">Population:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">{study.methods.population}</p>
              </div>
            )}
            {study.methods.exposure_definition && (
              <div className="col-span-2">
                <span className="text-slate-600 dark:text-slate-400">Exposure Definition:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">{study.methods.exposure_definition}</p>
              </div>
            )}
            {study.methods.outcome_definition && (
              <div className="col-span-2">
                <span className="text-slate-600 dark:text-slate-400">Outcome Definition:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">{study.methods.outcome_definition}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {study.analysis && (
        <div className="pb-4">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Analysis</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            {study.analysis.exposure && (
              <div>
                <span className="text-slate-600 dark:text-slate-400">Exposure:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.exposure}</p>
              </div>
            )}
            {study.analysis.outcome && (
              <div>
                <span className="text-slate-600 dark:text-slate-400">Outcome:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.outcome}</p>
              </div>
            )}

            {/* Generic effect measure display */}
            {study.analysis.effect_measure && study.analysis.effect_value && (
              <div className="col-span-2 bg-slate-50 dark:bg-slate-700/50 p-3 rounded">
                <span className="text-slate-600 dark:text-slate-400">Effect Measure:</span>
                <p className="text-slate-900 dark:text-slate-100 font-bold text-lg">
                  {study.analysis.effect_measure} = {study.analysis.effect_value}
                  {study.analysis.ci_lower && study.analysis.ci_upper && (
                    <span className="text-sm font-normal">
                      {" "}(95% CI: {study.analysis.ci_lower} - {study.analysis.ci_upper})
                    </span>
                  )}
                </p>
              </div>
            )}

            {/* Proportion-specific display */}
            {study.analysis.proportion_data && (
              <div className="col-span-2 bg-emerald-50 dark:bg-emerald-900/20 p-3 rounded border border-emerald-200 dark:border-emerald-800">
                <h4 className="font-semibold text-emerald-800 dark:text-emerald-300 mb-2">Proportion Data</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {study.analysis.proportion_data.events !== undefined && (
                    <div>
                      <span className="text-slate-600 dark:text-slate-400">Events:</span>
                      <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.proportion_data.events}</p>
                    </div>
                  )}
                  {study.analysis.proportion_data.sample_size !== undefined && (
                    <div>
                      <span className="text-slate-600 dark:text-slate-400">Sample Size:</span>
                      <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.proportion_data.sample_size}</p>
                    </div>
                  )}
                  {study.analysis.proportion_data.proportion !== undefined && (
                    <div>
                      <span className="text-slate-600 dark:text-slate-400">Proportion:</span>
                      <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.proportion_data.proportion.toFixed(4)}</p>
                    </div>
                  )}
                  {study.analysis.proportion_data.se !== undefined && (
                    <div>
                      <span className="text-slate-600 dark:text-slate-400">SE:</span>
                      <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.proportion_data.se.toFixed(4)}</p>
                    </div>
                  )}
                  {study.analysis.proportion_data.ci_lower !== undefined && study.analysis.proportion_data.ci_upper !== undefined && (
                    <div className="col-span-2">
                      <span className="text-slate-600 dark:text-slate-400">95% CI:</span>
                      <p className="text-slate-900 dark:text-slate-100 font-medium">
                        {study.analysis.proportion_data.ci_lower.toFixed(4)} — {study.analysis.proportion_data.ci_upper.toFixed(4)}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 2×2 Table display (for OR/RR) */}
            {study.analysis.two_by_two_table && (
              <div className="col-span-2 bg-amber-50 dark:bg-amber-900/20 p-3 rounded border border-amber-200 dark:border-amber-800">
                <h4 className="font-semibold text-amber-800 dark:text-amber-300 mb-2">2×2 Contingency Table</h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm border-collapse">
                    <thead>
                      <tr className="border-b border-amber-200 dark:border-amber-800">
                        <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-400"></th>
                        <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-400">Outcome +</th>
                        <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-400">Outcome −</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-amber-100 dark:border-amber-900">
                        <td className="px-3 py-2 font-medium text-slate-700 dark:text-slate-300">Exposed</td>
                        <td className="px-3 py-2 text-slate-900 dark:text-slate-100">{study.analysis.two_by_two_table.a ?? "—"}</td>
                        <td className="px-3 py-2 text-slate-900 dark:text-slate-100">{study.analysis.two_by_two_table.b ?? "—"}</td>
                      </tr>
                      <tr>
                        <td className="px-3 py-2 font-medium text-slate-700 dark:text-slate-300">Control</td>
                        <td className="px-3 py-2 text-slate-900 dark:text-slate-100">{study.analysis.two_by_two_table.c ?? "—"}</td>
                        <td className="px-3 py-2 text-slate-900 dark:text-slate-100">{study.analysis.two_by_two_table.d ?? "—"}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Continuous data display (for MD/SMD) */}
            {study.analysis.continuous_data && (
              <div className="col-span-2 bg-violet-50 dark:bg-violet-900/20 p-3 rounded border border-violet-200 dark:border-violet-800">
                <h4 className="font-semibold text-violet-800 dark:text-violet-300 mb-2">Continuous Data</h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm border-collapse">
                    <thead>
                      <tr className="border-b border-violet-200 dark:border-violet-800">
                        <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-400">Group</th>
                        <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-400">N</th>
                        <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-400">Mean</th>
                        <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-400">SD</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-violet-100 dark:border-violet-900">
                        <td className="px-3 py-2 font-medium text-slate-700 dark:text-slate-300">Exposed</td>
                        <td className="px-3 py-2 text-slate-900 dark:text-slate-100">{study.analysis.continuous_data.exposed_n ?? "—"}</td>
                        <td className="px-3 py-2 text-slate-900 dark:text-slate-100">{study.analysis.continuous_data.exposed_mean?.toFixed(2) ?? "—"}</td>
                        <td className="px-3 py-2 text-slate-900 dark:text-slate-100">{study.analysis.continuous_data.exposed_sd?.toFixed(2) ?? "—"}</td>
                      </tr>
                      <tr>
                        <td className="px-3 py-2 font-medium text-slate-700 dark:text-slate-300">Control</td>
                        <td className="px-3 py-2 text-slate-900 dark:text-slate-100">{study.analysis.continuous_data.control_n ?? "—"}</td>
                        <td className="px-3 py-2 text-slate-900 dark:text-slate-100">{study.analysis.continuous_data.control_mean?.toFixed(2) ?? "—"}</td>
                        <td className="px-3 py-2 text-slate-900 dark:text-slate-100">{study.analysis.continuous_data.control_sd?.toFixed(2) ?? "—"}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Survival data display (for HR) */}
            {study.analysis.survival_data && (
              <div className="col-span-2 bg-rose-50 dark:bg-rose-900/20 p-3 rounded border border-rose-200 dark:border-rose-800">
                <h4 className="font-semibold text-rose-800 dark:text-rose-300 mb-2">Survival Data</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {study.analysis.survival_data.events_exposed !== undefined && (
                    <div>
                      <span className="text-slate-600 dark:text-slate-400">Events (Exposed):</span>
                      <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.survival_data.events_exposed}</p>
                    </div>
                  )}
                  {study.analysis.survival_data.events_control !== undefined && (
                    <div>
                      <span className="text-slate-600 dark:text-slate-400">Events (Control):</span>
                      <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.survival_data.events_control}</p>
                    </div>
                  )}
                  {study.analysis.survival_data.person_time_exposed !== undefined && (
                    <div>
                      <span className="text-slate-600 dark:text-slate-400">Person-Time (Exposed):</span>
                      <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.survival_data.person_time_exposed.toFixed(1)}</p>
                    </div>
                  )}
                  {study.analysis.survival_data.person_time_control !== undefined && (
                    <div>
                      <span className="text-slate-600 dark:text-slate-400">Person-Time (Control):</span>
                      <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.survival_data.person_time_control.toFixed(1)}</p>
                    </div>
                  )}
                  {study.analysis.survival_data.rate_exposed !== undefined && (
                    <div>
                      <span className="text-slate-600 dark:text-slate-400">Rate (Exposed):</span>
                      <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.survival_data.rate_exposed.toFixed(6)}</p>
                    </div>
                  )}
                  {study.analysis.survival_data.rate_control !== undefined && (
                    <div>
                      <span className="text-slate-600 dark:text-slate-400">Rate (Control):</span>
                      <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.survival_data.rate_control.toFixed(6)}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Adjustment variables */}
            {study.analysis.adjustment_variables && study.analysis.adjustment_variables.length > 0 && (
              <div className="col-span-2">
                <span className="text-slate-600 dark:text-slate-400">Adjustment Variables:</span>
                <p className="text-slate-900 dark:text-slate-100 font-medium">{study.analysis.adjustment_variables.join(", ")}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {study.processing_time_ms && (
        <div className="text-xs text-slate-500 dark:text-slate-400 mt-4">
          Processing time: {study.processing_time_ms.toFixed(0)}ms
        </div>
      )}
    </div>
  );
});

const DownloadButton = memo(function DownloadButton({
  onClick,
  disabled,
  loading,
}: {
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className="px-4 py-2 bg-green-600 dark:bg-green-500 text-white rounded-lg hover:bg-green-700 dark:hover:bg-green-600 disabled:bg-slate-400 dark:disabled:bg-slate-600 disabled:cursor-not-allowed transition font-medium flex items-center gap-2"
    >
      {loading ? (
        <Spinner className="w-5 h-5" />
      ) : (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
      )}
      {loading ? "Downloading..." : "Download CSV"}
    </button>
  );
});

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ResultsPage() {
  const router = useRouter();
  const studies = useAppStore((s) => s.studies);
  const setStudies = useAppStore((s) => s.setStudies);
  const accessToken = useAppStore((s) => s.accessToken);
  const authChecked = useAppStore((s) => s.authChecked);

  const [loading, setLoading] = useState(false);
  const [downloadingCsv, setDownloadingCsv] = useState(false);

  useEffect(() => {
    if (!accessToken) {
      if (authChecked) router.push("/auth");
      return;
    }

    if (studies.length === 0) {
      setLoading(true);
      api.studies
        .list()
        .then(({ data }) => setStudies(data.studies || []))
        .catch(() => {/* 401 handled by interceptor */})
        .finally(() => setLoading(false));
    }
  }, [studies.length, setStudies, accessToken, authChecked, router]);

  const handleDownloadCsv = useCallback(async () => {
    if (!accessToken) {
      alert("Please sign in to download CSV files");
      return;
    }
    setDownloadingCsv(true);
    try {
      const response = await api.studies.exportCsv();
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "epi_studies_export.csv");
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch {
      alert("Failed to download CSV file");
    } finally {
      setDownloadingCsv(false);
    }
  }, [accessToken]);

  if (loading && studies.length === 0) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">Extraction Results</h1>
            <p className="text-slate-600 dark:text-slate-400">Loading studies...</p>
          </div>
        </div>
        <div className="grid gap-6">
          <StudyCardSkeleton />
          <StudyCardSkeleton />
          <StudyCardSkeleton />
        </div>
      </div>
    );
  }

  if (studies.length === 0) {
    return (
      <div className="p-8 text-center">
        <p className="text-slate-600 dark:text-slate-400">No studies extracted yet. Upload files to get started.</p>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="p-6 space-y-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">Extraction Results</h1>
            <p className="text-slate-600 dark:text-slate-400">{studies.length} studies extracted</p>
          </div>
          <DownloadButton
            onClick={handleDownloadCsv}
            disabled={studies.length === 0}
            loading={downloadingCsv}
          />
        </div>

        <div className="grid gap-6">
          {studies.map((study) => (
            <StudyCard key={study._id} study={study} />
          ))}
        </div>
      </div>
    </ErrorBoundary>
  );
}
