"use client";

import { memo, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import { loadAuthFromStorage } from "@/lib/auth";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ProjectCardSkeleton, FullPageLoader } from "@/components/ui/Skeleton";
import { EffectSelector } from "@/components/EffectSelector";
import { ZipUploader } from "@/components/ZipUploader";
import { ExtractionProgress } from "@/components/ExtractionProgress";
import type { MetaAnalysis } from "@/lib/api";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const ProjectList = memo(function ProjectList({
  projects,
  onSelect,
}: {
  projects: MetaAnalysis[];
  onSelect: (project: MetaAnalysis) => void;
}) {
  return (
    <div className="mt-6">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3">
        Or select an existing project:
      </h2>
      <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
        {projects.map((project) => (
          <button
            key={project.meta_analysis_id}
            onClick={() => onSelect(project)}
            className="w-full text-left p-4 border border-slate-200 dark:border-slate-700 bg-white/90 dark:bg-slate-900/70 rounded-2xl hover:bg-cyan-50 dark:hover:bg-slate-800 hover:border-cyan-300 dark:hover:border-cyan-700 transition"
          >
            <div className="font-semibold text-slate-900 dark:text-slate-100 truncate">
              {project.title}
            </div>
            <div className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              <span className="font-medium">ID:</span>{" "}
              {project.meta_analysis_id}
            </div>
            {project.outcome && project.exposure && (
              <div className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                <span className="font-medium">Variables:</span>{" "}
                {project.exposure} → {project.outcome}
              </div>
            )}
            <div className="text-xs text-slate-500 dark:text-slate-500 mt-1">
              {project.study_count || 0} studies · Created{" "}
              {project.created_at
                ? new Date(project.created_at).toLocaleDateString()
                : "N/A"}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
});

const DeleteDialog = memo(function DeleteDialog({
  title,
  studyCount,
  isDeleting,
  onCancel,
  onConfirm,
}: {
  title: string;
  studyCount: number;
  isDeleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50"
    >
      <div className="surface-card rounded-2xl p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">
          Delete Project
        </h3>
        <p className="text-slate-700 dark:text-slate-300 mb-6">
          Are you sure you want to delete <strong>{title}</strong>? This will
          permanently delete the project and all {studyCount} associated
          studies. This action cannot be undone.
        </p>
        <div className="flex gap-4">
          <button
            onClick={onCancel}
            disabled={isDeleting}
            className="flex-1 px-4 py-2 bg-slate-300 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-xl hover:bg-slate-400 dark:hover:bg-slate-600 transition font-medium disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="flex-1 px-4 py-2 bg-red-500 dark:bg-red-600 text-white rounded-xl hover:bg-red-600 dark:hover:bg-red-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
});

const MetaAnalysisHeader = memo(function MetaAnalysisHeader({
  metaAnalysis,
  onBack,
  onDelete,
}: {
  metaAnalysis: MetaAnalysis;
  onBack: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="surface-card rounded-2xl p-5 sm:p-6">
      <div className="flex justify-between items-start">
        <div className="flex-1 min-w-0">
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2 truncate">
            {metaAnalysis.title}
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
            <strong>Project ID:</strong> {metaAnalysis.meta_analysis_id}
          </p>
          {metaAnalysis.outcome && metaAnalysis.exposure && (
            <p className="text-sm text-slate-700 dark:text-slate-300 mb-2">
              <strong>Variables:</strong> {metaAnalysis.exposure} →{" "}
              {metaAnalysis.outcome}
            </p>
          )}
          {metaAnalysis.details && (
            <p className="text-sm text-slate-700 dark:text-slate-300 mb-2">
              <strong>Details:</strong> {metaAnalysis.details}
            </p>
          )}
        </div>
        <div className="ml-4 flex gap-2 shrink-0">
          <button
            onClick={onBack}
            className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-full hover:bg-slate-300 dark:hover:bg-slate-600 transition font-medium text-sm"
          >
            Back
          </button>
          <button
            onClick={onDelete}
            className="px-4 py-2 bg-red-500 dark:bg-red-600 text-white rounded-full hover:bg-red-600 dark:hover:bg-red-700 transition font-medium text-sm"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
});

const EmptyState = memo(function EmptyState({
  onCreate,
}: {
  onCreate: () => void;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className="py-4 sm:py-8"
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
      transition={reduceMotion ? undefined : { duration: 0.45 }}
    >
      <div className="surface-card rounded-3xl p-6 sm:p-8 lg:p-10 max-w-4xl w-full mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-wide text-cyan-700 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800 mb-4">
          AI-Powered Epidemiology Workspace
        </div>

        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-slate-900 dark:text-slate-100 leading-tight mb-4">
          Turn study PDFs into clean meta-analysis inputs.
        </h1>
        <p className="text-base sm:text-lg text-slate-600 dark:text-slate-400 mb-8 max-w-3xl">
          Begin by creating a new meta-analysis project or select an existing
          one.
        </p>

        <button
          onClick={onCreate}
          className="w-full sm:w-auto px-7 py-3.5 bg-linear-to-r from-cyan-600 to-teal-600 text-white text-base font-semibold rounded-full hover:from-cyan-500 hover:to-teal-500 transition mb-6 shadow"
        >
          Create New Meta-Analysis
        </button>

        <div className="mt-8 bg-cyan-50 dark:bg-cyan-900/15 border border-cyan-200 dark:border-cyan-800 rounded-2xl p-5">
          <h3 className="font-semibold text-cyan-900 dark:text-cyan-300 mb-2">
            What you can do:
          </h3>
          <ul className="text-sm text-cyan-800 dark:text-cyan-400 space-y-2">
            <li>✓ Create a meta-analysis project with a title and research notes</li>
            <li>✓ Upload multiple PDF files or ZIP archives of studies</li>
            <li>✓ Automatically extract epidemiologic data from each study</li>
            <li>✓ Download results as CSV for analysis</li>
            <li>✓ Retrieve your results anytime using your project ID</li>
          </ul>
        </div>
      </div>
    </motion.div>
  );
});

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function Home() {
  const router = useRouter();
  const reduceMotion = useReducedMotion();

  const metaAnalysis = useAppStore((s) => s.metaAnalysis);
  const accessToken = useAppStore((s) => s.accessToken);
  const authChecked = useAppStore((s) => s.authChecked);
  const setMetaAnalysis = useAppStore((s) => s.setMetaAnalysis);
  const clearMetaAnalysis = useAppStore((s) => s.clearMetaAnalysis);

  const [existingProjects, setExistingProjects] = useState<MetaAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Auth check + project fetch
  useEffect(() => {
    if (!authChecked) return;

    let tokenToUse = accessToken;
    if (!tokenToUse) {
      const { token } = loadAuthFromStorage();
      if (token) tokenToUse = token;
    }

    if (!tokenToUse) {
      router.push("/auth");
      return;
    }

    if (!metaAnalysis) {
      fetchProjects();
    } else {
      setLoading(false);
    }
  }, [metaAnalysis, accessToken, authChecked, router]);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.metaAnalyses.list();
      setExistingProjects(data.meta_analyses || []);
    } catch {
      // 401 is handled by interceptor
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSelectProject = useCallback(
    (project: MetaAnalysis) => {
      setMetaAnalysis(project);
    },
    [setMetaAnalysis]
  );

  const handleDeleteProject = useCallback(async () => {
    if (!metaAnalysis?.meta_analysis_id) return;

    setIsDeleting(true);
    try {
      await api.metaAnalyses.delete(metaAnalysis.meta_analysis_id);
      clearMetaAnalysis();
      fetchProjects();
      setShowDeleteConfirm(false);
    } catch {
      alert("Failed to delete project. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  }, [metaAnalysis, clearMetaAnalysis, fetchProjects]);

  const handleBack = useCallback(() => {
    clearMetaAnalysis();
    fetchProjects();
  }, [clearMetaAnalysis, fetchProjects]);

  const handleCreate = useCallback(() => {
    router.push("/new-meta-analysis");
  }, [router]);

  // ------------------------------------------------------------------
  // Render: No project selected
  // ------------------------------------------------------------------

  if (!metaAnalysis) {
    return (
      <ErrorBoundary>
        <EmptyState onCreate={handleCreate} />
        {loading ? (
          <div className="mt-6 space-y-2.5 max-w-4xl mx-auto">
            <ProjectCardSkeleton />
            <ProjectCardSkeleton />
            <ProjectCardSkeleton />
          </div>
        ) : existingProjects.length > 0 ? (
          <div className="max-w-4xl mx-auto">
            <ProjectList
              projects={existingProjects}
              onSelect={handleSelectProject}
            />
          </div>
        ) : null}
      </ErrorBoundary>
    );
  }

  // ------------------------------------------------------------------
  // Render: Project selected
  // ------------------------------------------------------------------

  return (
    <ErrorBoundary>
      <motion.div
        className="space-y-8"
        initial={reduceMotion ? false : { opacity: 0, y: 10 }}
        animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
        transition={reduceMotion ? undefined : { duration: 0.45 }}
      >
        <MetaAnalysisHeader
          metaAnalysis={metaAnalysis}
          onBack={handleBack}
          onDelete={() => setShowDeleteConfirm(true)}
        />

        {showDeleteConfirm && (
          <DeleteDialog
            title={metaAnalysis.title}
            studyCount={metaAnalysis.study_count || 0}
            isDeleting={isDeleting}
            onCancel={() => setShowDeleteConfirm(false)}
            onConfirm={handleDeleteProject}
          />
        )}

        <h1 className="text-2xl sm:text-3xl font-semibold text-slate-900 dark:text-slate-100">
          Automated Epidemiologic Meta-Extraction
        </h1>

        <EffectSelector />
        <ZipUploader />
        <ExtractionProgress />
      </motion.div>
    </ErrorBoundary>
  );
}

