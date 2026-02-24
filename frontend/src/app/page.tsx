"use client";

import { EffectSelector } from "@/components/EffectSelector";
import { ZipUploader } from "@/components/ZipUploader";
import { ExtractionProgress } from "@/components/ExtractionProgress";
import { useAppStore } from "@/store/useAppStore";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE_URL, buildAuthHeaders } from "@/lib/api";
import { loadAuthFromStorage } from "@/lib/auth";

export default function Home() {
  const { metaAnalysis, setMetaAnalysis, clearMetaAnalysis, accessToken, authChecked } = useAppStore();
  const router = useRouter();
  const [existingProjects, setExistingProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    const initPage = async () => {
      console.log("[useEffect Home]", {
        hasAccessToken: !!accessToken,
        accessToken: accessToken ? accessToken.substring(0, 20) + "..." : "null",
        authChecked,
        hasMetaAnalysis: !!metaAnalysis,
      });
      
      // Wait for auth check to complete before deciding what to do
      if (!authChecked) {
        console.log("[useEffect Home] Auth not checked yet, waiting...");
        return;
      }
      
      // If store doesn't have token but localStorage does, use localStorage version
      let tokenToUse = accessToken;
      if (!tokenToUse) {
        const { token } = loadAuthFromStorage();
        if (token) {
          console.log("[useEffect Home] Token not in store, loaded from storage");
          tokenToUse = token;
        }
      }
      
      if (!tokenToUse) {
        console.log("[useEffect Home] No access token found, redirecting to auth");
        router.push("/auth");
        return;
      }
      
      // Fetch existing meta-analyses if no current project
      if (!metaAnalysis) {
        console.log("[useEffect Home] Fetching existing projects");
        await fetchExistingProjects(tokenToUse);
      } else {
        console.log("[useEffect Home] Meta-analysis already set");
        setLoading(false);
      }
    };

    initPage();
  }, [metaAnalysis, accessToken, authChecked, router]);

  const fetchExistingProjects = async (token?: string | null) => {
    try {
      const url = `${API_BASE_URL}/meta-analyses`;
      // Use provided token or fallback to accessToken or localStorage
      const tokenToUse = token || accessToken;
      const headers = buildAuthHeaders(tokenToUse);
      
      console.log("[fetchExistingProjects]", {
        url,
        hasAccessToken: !!accessToken,
        hasProvidedToken: !!token,
        tokenToUse: tokenToUse ? tokenToUse.substring(0, 20) + "..." : "null",
        hasAuthHeader: !!headers.Authorization,
      });
      
      const response = await axios.get(url, { headers });
      console.log("[fetchExistingProjects] Success:", response.data);
      setExistingProjects(response.data.meta_analyses || []);
    } catch (error) {
      console.error("[fetchExistingProjects] Error:", error);
      
      if (axios.isAxiosError(error)) {
        console.error("[fetchExistingProjects] Response:", {
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
        });
        
        // Handle 401 specifically - token expired or invalid
        if (error.response?.status === 401) {
          console.error("[fetchExistingProjects] Auth failed - clearing auth and redirecting");
          // Clear expired token
          if (typeof window !== "undefined") {
            window.localStorage.removeItem("epi_access_token");
            window.localStorage.removeItem("epi_user");
          }
          // Clear store
          const { clearAuth } = useAppStore.getState();
          clearAuth();
          // Redirect to login
          router.push("/auth");
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSelectProject = (project: any) => {
    setMetaAnalysis({
      meta_analysis_id: project.meta_analysis_id,
      title: project.title,
      details: project.details,
      outcome: project.outcome,
      exposure: project.exposure,
      created_at: project.created_at,
    });
  };

  const handleDeleteProject = async () => {
    if (!metaAnalysis?.meta_analysis_id || !accessToken) {
      return;
    }

    setIsDeleting(true);
    try {
      const url = `${API_BASE_URL}/meta-analyses/${metaAnalysis.meta_analysis_id}`;
      console.log("[Delete] URL:", url);
      console.log("[Delete] Headers:", buildAuthHeaders(accessToken));
      
      const response = await axios.delete(url, {
        headers: buildAuthHeaders(accessToken),
      });

      console.log("[Delete] Response:", response.data);

      if (response.data.status === "success") {
        // Clear the current meta-analysis from the store
        clearMetaAnalysis();
        // Refresh the projects list
        fetchExistingProjects();
        setShowDeleteConfirm(false);
      }
    } catch (error) {
      console.error("Failed to delete project:", error);
      
      let errorMessage = "Failed to delete project. Please try again.";
      if (axios.isAxiosError(error)) {
        console.error("Error details:", {
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
          message: error.message,
        });
        if (error.response?.status === 404) {
          errorMessage = "Project not found. It may have already been deleted.";
        } else if (error.response?.status === 401) {
          errorMessage = "You are not authenticated. Please log in again.";
        } else if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        }
      }
      alert(errorMessage);
    } finally {
      setIsDeleting(false);
    }
  };

  if (!metaAnalysis) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-6">
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8 max-w-2xl w-full">
          <h1 className="text-4xl font-bold text-slate-900 dark:text-slate-100 mb-4">Welcome to Epi Meta Extractor</h1>
          <p className="text-lg text-slate-600 dark:text-slate-400 mb-8">
            Begin by creating a new meta-analysis project or select an existing one.
          </p>

          <button
            onClick={() => router.push("/new-meta-analysis")}
            className="w-full px-6 py-4 bg-blue-600 dark:bg-blue-500 text-white text-lg font-semibold rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition mb-6"
          >
            Create New Meta-Analysis
          </button>

          {/* Existing Projects */}
          {loading ? (
            <div className="text-center py-4 text-slate-500 dark:text-slate-400">
              Loading existing projects...
            </div>
          ) : existingProjects.length > 0 ? (
            <div className="mt-6">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3">
                Or select an existing project:
              </h2>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {existingProjects.map((project) => (
                  <button
                    key={project.meta_analysis_id}
                    onClick={() => handleSelectProject(project)}
                    className="w-full text-left p-4 border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 rounded-lg hover:bg-blue-50 dark:hover:bg-slate-600 hover:border-blue-300 dark:hover:border-blue-500 transition"
                  >
                    <div className="font-semibold text-slate-900 dark:text-slate-100">{project.title}</div>
                    <div className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                      <span className="font-medium">ID:</span> {project.meta_analysis_id}
                    </div>
                    {project.outcome && project.exposure && (
                      <div className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                        <span className="font-medium">Variables:</span> {project.exposure} → {project.outcome}
                      </div>
                    )}
                    <div className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                      {project.study_count || 0} studies · Created {new Date(project.created_at).toLocaleDateString()}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 dark:text-blue-300 mb-2">What you can do:</h3>
            <ul className="text-sm text-blue-800 dark:text-blue-400 space-y-2">
              <li>✓ Create a meta-analysis project with a title and research notes</li>
              <li>✓ Upload multiple PDF files or ZIP archives of studies</li>
              <li>✓ Automatically extract epidemiologic data from each study</li>
              <li>✓ Download results as CSV for analysis</li>
              <li>✓ Retrieve your results anytime using your project ID</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Meta-Analysis Header */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2">
              {metaAnalysis.title}
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
              <strong>Project ID:</strong> {metaAnalysis.meta_analysis_id}
            </p>
            {metaAnalysis.outcome && metaAnalysis.exposure && (
              <p className="text-sm text-slate-700 dark:text-slate-300 mb-2">
                <strong>Variables:</strong> {metaAnalysis.exposure} → {metaAnalysis.outcome}
              </p>
            )}
            {metaAnalysis.details && (
              <p className="text-sm text-slate-700 dark:text-slate-300 mb-2">
                <strong>Details:</strong> {metaAnalysis.details}
              </p>
            )}
          </div>
          <div className="ml-4 flex gap-2">
            <button
              onClick={() => {
                clearMetaAnalysis();
                fetchExistingProjects();
              }}
              className="px-4 py-2 bg-slate-300 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded hover:bg-slate-400 dark:hover:bg-slate-500 transition font-medium text-sm"
            >
              Back to Projects
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-4 py-2 bg-red-500 dark:bg-red-600 text-white rounded hover:bg-red-600 dark:hover:bg-red-700 transition font-medium text-sm"
            >
              Delete Project
            </button>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-800 rounded-lg p-6 max-w-md w-full mx-4 shadow-lg">
            <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Delete Project</h3>
            <p className="text-slate-700 dark:text-slate-300 mb-6">
              Are you sure you want to delete the project <strong>{metaAnalysis.title}</strong>? 
              This will permanently delete the project and all {metaAnalysis.study_count || 0} associated studies. 
              This action cannot be undone.
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
                className="flex-1 px-4 py-2 bg-slate-300 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded hover:bg-slate-400 dark:hover:bg-slate-500 transition font-medium disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteProject}
                disabled={isDeleting}
                className="flex-1 px-4 py-2 bg-red-500 dark:bg-red-600 text-white rounded hover:bg-red-600 dark:hover:bg-red-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDeleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
        Automated Epidemiologic Meta-Extraction
      </h1>

      <EffectSelector />
      <ZipUploader />
      <ExtractionProgress />
    </div>
  );
}

