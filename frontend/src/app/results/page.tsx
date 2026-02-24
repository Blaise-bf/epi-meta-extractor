"use client";

import { useAppStore } from "@/store/useAppStore";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { API_BASE_URL, buildAuthHeaders } from "@/lib/api";

export default function ResultsPage() {
  const { studies, setStudies, accessToken, authChecked } = useAppStore();
  const [loadingMoreStudies, setLoadingMoreStudies] = useState(false);
  const [downloadingCsv, setDownloadingCsv] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (!accessToken) {
      if (authChecked) {
        router.push("/auth");
      }
      return;
    }
    // Fetch all studies from the backend when the page loads
    const fetchStudies = async () => {
      setLoadingMoreStudies(true);
      try {
        const response = await axios.get(`${API_BASE_URL}/studies`, {
          headers: buildAuthHeaders(accessToken),
        });
        setStudies(response.data.studies || []);
      } catch (error) {
        console.error("Failed to fetch studies:", error);
      } finally {
        setLoadingMoreStudies(false);
      }
    };

    // Only fetch if we don't have studies yet
    if (studies.length === 0) {
      fetchStudies();
    }
  }, [studies.length, setStudies, accessToken, authChecked, router]);

  const handleDownloadCsv = async () => {
    if (!accessToken) {
      alert("Please sign in to download CSV files");
      return;
    }
    setDownloadingCsv(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/studies/export/csv`, {
        responseType: "blob",
        headers: buildAuthHeaders(accessToken),
      });
      
      // Create a blob and download it
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "epi_studies_export.csv");
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to download CSV:", error);
      alert("Failed to download CSV file");
    } finally {
      setDownloadingCsv(false);
    }
  };

  if (loadingMoreStudies && studies.length === 0) {
    return (
      <div className="p-8 text-center">
        <p className="text-slate-600 dark:text-slate-400">Loading studies...</p>
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
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">Extraction Results</h1>
          <p className="text-slate-600 dark:text-slate-400">{studies.length} studies extracted</p>
        </div>
        <button
          onClick={handleDownloadCsv}
          disabled={downloadingCsv || studies.length === 0}
          className="px-4 py-2 bg-green-600 dark:bg-green-500 text-white rounded-lg hover:bg-green-700 dark:hover:bg-green-600 disabled:bg-slate-400 dark:disabled:bg-slate-600 disabled:cursor-not-allowed transition font-medium flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {downloadingCsv ? "Downloading..." : "Download CSV"}
        </button>
      </div>

      <div className="grid gap-6">
        {studies.map((study) => (
          <div key={study._id} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-6 shadow-sm hover:shadow-md dark:hover:shadow-slate-900/20 transition">
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

            {/* Metadata Section */}
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
                </div>
              </div>
            )}

            {/* Methods Section */}
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
                </div>
              </div>
            )}

            {/* Analysis Section */}
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
                </div>
              </div>
            )}

            {/* Metadata Footer */}
            {study.processing_time_ms && (
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-4">
                Processing time: {study.processing_time_ms.toFixed(0)}ms
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
