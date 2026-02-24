"use client";

import { useDropzone } from "react-dropzone";
import axios from "axios";
import { useAppStore } from "@/store/useAppStore";
import { useState, useEffect, useRef } from "react";
import { API_BASE_URL, buildAuthHeaders } from "@/lib/api";

export const ZipUploader = () => {
  const { effectType, metaAnalysis, addStudy, accessToken, setProgress } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [outcome, setOutcome] = useState(metaAnalysis?.outcome || "");
  const [exposure, setExposure] = useState(metaAnalysis?.exposure || "");
  const [batchId, setBatchId] = useState<string | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Update outcome/exposure when metaAnalysis changes
  useEffect(() => {
    if (metaAnalysis?.outcome) setOutcome(metaAnalysis.outcome);
    if (metaAnalysis?.exposure) setExposure(metaAnalysis.exposure);
  }, [metaAnalysis]);

  // Poll for batch progress
  useEffect(() => {
    if (!batchId || !accessToken) return;

    let errorCount = 0;
    const maxConsecutiveErrors = 5;

    const pollBatchProgress = async () => {
      try {
        const url = `${API_BASE_URL}/batch/${batchId}`;
        console.log("[Polling]", url);
        
        const response = await axios.get(url, {
          headers: buildAuthHeaders(accessToken),
          timeout: 60000, // 60 second timeout (increased to handle slow semantic search processing)
        });

        errorCount = 0; // Reset error count on success
        const { processed_count, total_files, status, current_file } = response.data;

        // Update progress in store
        setProgress({
          processed: processed_count,
          total: total_files,
          currentArticle: current_file || undefined,
        });

        // Stop polling when completed
        if (status === "completed" || status === "failed" || status === "partial") {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          setLoading(false);

          if (status === "completed") {
            setSuccess(
              `Batch job completed! Successfully processed ${processed_count} / ${total_files} files.`
            );
          } else if (status === "partial") {
            setSuccess(
              `Batch job completed with partial success! Processed ${processed_count} / ${total_files} files.`
            );
          } else {
            setError("Batch job failed. Please check the logs for details.");
          }

          setBatchId(null);
        }
      } catch (err) {
        errorCount++;
        console.error(`[Polling Error ${errorCount}/${maxConsecutiveErrors}]:`, err);
        
        // Check if it's a timeout error
        if (axios.isAxiosError(err) && err.code === 'ECONNABORTED') {
          console.warn("[Polling] Request timed out, will retry...");
        }
        
        if (errorCount >= maxConsecutiveErrors) {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          setLoading(false);
          const backendUrl = API_BASE_URL;
          setError(
            `Backend server is not responding at ${backendUrl}. ` +
            `Please ensure the backend is running: python -m uvicorn backend.app:app --reload --port 8001`
          );
          setBatchId(null);
        }
      }
    };

    // Poll immediately and then every 3 seconds (reduced frequency for slower processing)
    pollBatchProgress();
    pollingIntervalRef.current = setInterval(pollBatchProgress, 3000);

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [batchId, accessToken, setProgress]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const onDrop = async (acceptedFiles: File[]) => {
    setError(null);
    setSuccess(null);

    if (!effectType) {
      setError("Please select an effect type first.");
      return;
    }

    if (!outcome.trim() || !exposure.trim()) {
      setError("Please specify both outcome and exposure variables.");
      return;
    }

    if (!acceptedFiles.length) {
      setError("No files selected.");
      return;
    }

    const file = acceptedFiles[0];

    if (!file.name.toLowerCase().endsWith(".zip") && !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please upload a ZIP archive or PDF file.");
      return;
    }

    if (!accessToken) {
      setError("Please sign in before uploading files.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);

    try {
      // Build query parameters
      const queryParams = new URLSearchParams();
      queryParams.append("effect_type", effectType);
      queryParams.append("outcome", outcome.trim());
      queryParams.append("exposure", exposure.trim());
      if (metaAnalysis?.meta_analysis_id) {
        queryParams.append("meta_analysis_id", metaAnalysis.meta_analysis_id);
      }

      const response = await axios.post(
        `${API_BASE_URL}/upload?${queryParams.toString()}`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
            ...buildAuthHeaders(accessToken),
          },
          timeout: 120000, // 120 second timeout for initial upload and extraction
        }
      );

      console.log("[Upload Response]", response.data);

      if (response.data.status === "batch_created") {
        // Set batch ID to start polling
        console.log("[Batch Created]", {
          batch_id: response.data.batch_id,
          num_files: response.data.num_files,
        });
        setBatchId(response.data.batch_id);
        setLoading(true);
        setSuccess(null);
        setError(null);
        // Initialize progress
        setProgress({
          processed: 0,
          total: response.data.num_files,
          currentArticle: undefined,
        });
      } else if (response.data.status === "not_relevant") {
        setLoading(false);
        setError(response.data.message || "Study is not relevant to the selected outcome/exposure.");
      } else if (response.data.status === "success") {
        setLoading(false);
        // Add the extracted study to the store
        const study = {
          _id: response.data.study_id,
          filename: response.data.file_name,
          effect_type: response.data.effect_type,
          metadata: response.data.extracted_data?.metadata,
          methods: response.data.extracted_data?.methods,
          analysis: response.data.extracted_data?.analysis,
          processing_time_ms: response.data.processing_time_ms,
        };
        addStudy(study);
        setSuccess(`File processed successfully! Study ID: ${response.data.study_id}`);
      }
    } catch (err) {
      let errorMessage = "An unexpected error occurred";
      
      if (axios.isAxiosError(err)) {
        console.error("Upload error details:", {
          message: err.message,
          code: err.code,
          status: err.response?.status,
          statusText: err.response?.statusText,
          data: err.response?.data,
          headers: err.response?.headers,
          config: {
            url: err.config?.url,
            method: err.config?.method,
            headers: err.config?.headers,
          },
        });

        // Network errors (no response from server)
        if (err.code === 'ECONNABORTED') {
          errorMessage = "Request timeout - the server took too long to respond";
        } else if (err.code === 'ERR_NETWORK' || err.code === 'ENOTFOUND') {
          errorMessage = "Network error - cannot reach the server. Please check if the backend is running.";
        } else if (err.code === 'ERR_CONNECTION_REFUSED') {
          errorMessage = "Connection refused - the backend server is not responding";
        } else if (!err.response) {
          errorMessage = `Network error: ${err.message}`;
        } else if (err.response?.data?.detail) {
          errorMessage = err.response.data.detail;
        } else if (err.response?.data?.message) {
          errorMessage = err.response.data.message;
        } else if (typeof err.response?.data === "string" && err.response.data.trim()) {
          errorMessage = err.response.data;
        } else if (err.response?.statusText) {
          errorMessage = `${err.response.status} ${err.response.statusText}`;
        } else if (err.message) {
          errorMessage = err.message;
        }
      } else {
        errorMessage = err instanceof Error ? err.message : String(err);
        console.error("Upload error (non-Axios):", err);
      }
      
      setError(`Upload failed: ${errorMessage}`);
    } finally {
      // loading state is now managed by polling logic for batch jobs
      // only set to false for single file uploads or if no batch was created
      if (!batchId) {
        setLoading(false);
      }
    }
  };

  const { getRootProps, getInputProps } = useDropzone({
    accept: { "application/zip": [".zip"], "application/pdf": [".pdf"] },
    multiple: false,
    onDrop,
  });

  return (
    <div className="mt-6">
      {/* Outcome and Exposure Input Fields */}
      <div className="mb-4 space-y-3">
        <div>
          <label htmlFor="outcome" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Outcome Variable *
          </label>
          <input
            id="outcome"
            type="text"
            value={outcome}
            onChange={(e) => setOutcome(e.target.value)}
            placeholder="e.g., lung cancer, cardiovascular disease"
            className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500 dark:focus:ring-teal-400 transition-colors"
            disabled={loading}
          />
        </div>
        <div>
          <label htmlFor="exposure" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Exposure Variable *
          </label>
          <input
            id="exposure"
            type="text"
            value={exposure}
            onChange={(e) => setExposure(e.target.value)}
            placeholder="e.g., smoking, obesity, physical activity"
            className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500 dark:focus:ring-teal-400 transition-colors"
            disabled={loading}
          />
        </div>
      </div>

      <div
        {...getRootProps()}
        className={`p-8 border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-lg text-center bg-white dark:bg-slate-800 cursor-pointer transition ${
          loading ? "opacity-50 cursor-not-allowed" : "hover:bg-slate-50 dark:hover:bg-slate-700"
        }`}
      >
        <input {...getInputProps()} disabled={loading} />
        {loading ? (
          <div>
            <p className="text-sm text-slate-600 dark:text-slate-400">Processing...</p>
            <div className="mt-2 animate-spin inline-block">⏳</div>
          </div>
        ) : (
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Drag and drop a ZIP file or PDF, or click to select
          </p>
        )}
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-100 dark:bg-red-900/20 border border-red-400 dark:border-red-500 text-red-700 dark:text-red-400 rounded">
          <p className="text-sm font-semibold">Error</p>
          <p className="text-sm">{error}</p>
        </div>
      )}

      {success && (
        <div className="mt-4 p-4 bg-green-100 dark:bg-green-900/20 border border-green-400 dark:border-green-500 text-green-700 dark:text-green-400 rounded">
          <p className="text-sm font-semibold">Success</p>
          <p className="text-sm">{success}</p>
        </div>
      )}
    </div>
  );
};
