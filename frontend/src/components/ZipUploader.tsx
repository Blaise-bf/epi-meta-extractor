"use client";

import { memo, useCallback, useEffect, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/Skeleton";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const UploadZone = memo(function UploadZone({
  loading,
  getRootProps,
  getInputProps,
}: {
  loading: boolean;
  getRootProps: any;
  getInputProps: any;
}) {
  return (
    <div
      {...getRootProps()}
      className={`p-8 sm:p-10 border-2 border-dashed rounded-2xl text-center bg-linear-to-br from-cyan-50 to-blue-50 dark:from-slate-900 dark:to-slate-800 cursor-pointer transition ${
        loading
          ? "opacity-50 cursor-not-allowed border-slate-300 dark:border-slate-700"
          : "border-cyan-300 dark:border-cyan-700 hover:border-cyan-500 dark:hover:border-cyan-500 hover:shadow-sm"
      }`}
    >
      <input {...getInputProps()} disabled={loading} />
      {loading ? (
        <div className="flex flex-col items-center gap-3">
          <Spinner className="w-8 h-8" />
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Processing upload...
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-base font-semibold text-slate-900 dark:text-slate-100">
            Drop files here or click to browse
          </p>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Accepted formats: .zip and .pdf
          </p>
        </div>
      )}
    </div>
  );
});

const Alert = memo(function Alert({
  type,
  message,
}: {
  type: "error" | "success";
  message: string;
}) {
  const styles =
    type === "error"
      ? "bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-500 text-red-700 dark:text-red-400"
      : "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-300 dark:border-emerald-500 text-emerald-700 dark:text-emerald-400";

  return (
    <div className={`mt-4 p-4 border rounded-xl ${styles}`}>
      <p className="text-sm font-semibold capitalize">{type}</p>
      <p className="text-sm">{message}</p>
    </div>
  );
});

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export const ZipUploader = memo(function ZipUploader() {
  const effectType = useAppStore((s) => s.effectType);
  const metaAnalysis = useAppStore((s) => s.metaAnalysis);
  const accessToken = useAppStore((s) => s.accessToken);
  const addStudy = useAppStore((s) => s.addStudy);
  const setProgress = useAppStore((s) => s.setProgress);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [outcome, setOutcome] = useState(metaAnalysis?.outcome || "");
  const [exposure, setExposure] = useState(metaAnalysis?.exposure || "");
  const [batchId, setBatchId] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Sync outcome/exposure from metaAnalysis
  useEffect(() => {
    if (metaAnalysis?.outcome) setOutcome(metaAnalysis.outcome);
    if (metaAnalysis?.exposure) setExposure(metaAnalysis.exposure);
  }, [metaAnalysis]);

  // Poll for batch progress
  useEffect(() => {
    if (!batchId || !accessToken) return;

    let errorCount = 0;
    const maxErrors = 5;

    const poll = async () => {
      try {
        const { data } = await api.batch.getStatus(batchId);
        errorCount = 0;

        setProgress({
          processed: data.processed_count,
          total: data.total_files,
          currentArticle: data.current_file,
        });

        if (["completed", "failed", "partial"].includes(data.status)) {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          setLoading(false);

          if (data.status === "completed") {
            setSuccess(
              `Batch completed! Processed ${data.processed_count} / ${data.total_files} files.`
            );
          } else if (data.status === "partial") {
            setSuccess(
              `Batch completed with partial success! ${data.processed_count} / ${data.total_files} files.`
            );
          } else {
            setError("Batch job failed. Please check the logs.");
          }
          setBatchId(null);
        }
      } catch {
        errorCount++;
        if (errorCount >= maxErrors) {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          setLoading(false);
          setError("Backend server is not responding. Please ensure it is running.");
          setBatchId(null);
        }
      }
    };

    poll();
    pollingRef.current = setInterval(poll, 3000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [batchId, accessToken, setProgress]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
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
      const ext = file.name.toLowerCase();
      if (!ext.endsWith(".zip") && !ext.endsWith(".pdf")) {
        setError("Please upload a ZIP archive or PDF file.");
        return;
      }
      if (!accessToken) {
        setError("Please sign in before uploading files.");
        return;
      }

      const formData = new FormData();
      formData.append("file", file);

      const params = new URLSearchParams();
      params.append("effect_type", effectType);
      params.append("outcome", outcome.trim());
      params.append("exposure", exposure.trim());
      if (metaAnalysis?.meta_analysis_id) {
        params.append("meta_analysis_id", metaAnalysis.meta_analysis_id);
      }

      setLoading(true);

      try {
        const { data } = await api.upload(formData, params);

        if (data.status === "batch_created") {
          setBatchId(data.batch_id);
          setProgress({
            processed: 0,
            total: data.num_files,
            currentArticle: undefined,
          });
        } else if (data.status === "not_relevant") {
          setLoading(false);
          setError(data.message || "Study is not relevant.");
        } else if (data.status === "success") {
          setLoading(false);
          addStudy({
            _id: data.study_id,
            filename: data.file_name,
            effect_type: data.effect_type,
            metadata: data.extracted_data?.metadata,
            methods: data.extracted_data?.methods,
            analysis: data.extracted_data?.analysis,
            processing_time_ms: data.processing_time_ms,
          });
          setSuccess(`File processed! Study ID: ${data.study_id}`);
        }
      } catch (err: any) {
        setLoading(false);
        const msg =
          err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "Upload failed. Please try again.";
        setError(msg);
      }
    },
    [effectType, outcome, exposure, metaAnalysis, accessToken, addStudy, setProgress]
  );

  const { getRootProps, getInputProps } = useDropzone({
    accept: { "application/zip": [".zip"], "application/pdf": [".pdf"] },
    multiple: false,
    onDrop,
  });

  return (
    <section className="surface-card rounded-2xl p-5 sm:p-6 mt-6">
      <div className="mb-5">
        <h2 className="text-lg sm:text-xl font-semibold text-slate-900 dark:text-slate-100">
          Upload Studies
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Add a ZIP archive of PDFs or a single PDF. We will extract
          epidemiologic fields automatically.
        </p>
      </div>

      <div className="mb-5 grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="space-y-1">
          <label
            htmlFor="outcome"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
          >
            Outcome Variable *
          </label>
          <input
            id="outcome"
            type="text"
            value={outcome}
            onChange={(e) => setOutcome(e.target.value)}
            placeholder="e.g., lung cancer, cardiovascular disease"
            className="w-full px-3 py-2.5 border border-slate-300 dark:border-slate-600 bg-white/90 dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 rounded-xl focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:focus:ring-cyan-400 transition-colors"
            disabled={loading}
          />
        </div>
        <div className="space-y-1">
          <label
            htmlFor="exposure"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
          >
            Exposure Variable *
          </label>
          <input
            id="exposure"
            type="text"
            value={exposure}
            onChange={(e) => setExposure(e.target.value)}
            placeholder="e.g., smoking, obesity, physical activity"
            className="w-full px-3 py-2.5 border border-slate-300 dark:border-slate-600 bg-white/90 dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 rounded-xl focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:focus:ring-cyan-400 transition-colors"
            disabled={loading}
          />
        </div>
      </div>

      <UploadZone
        loading={loading}
        getRootProps={getRootProps}
        getInputProps={getInputProps}
      />

      {error && <Alert type="error" message={error} />}
      {success && <Alert type="success" message={success} />}
    </section>
  );
});
