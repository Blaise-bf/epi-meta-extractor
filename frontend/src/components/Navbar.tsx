"use client";

import Link from "next/link";
import { useTheme } from "next-themes";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useAppStore } from "@/store/useAppStore";
import axios from "axios";
import { API_BASE_URL } from "@/lib/api";
import { clearAuthStorage } from "@/lib/auth";

export const Navbar = () => {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const { metaAnalysis, authUser, accessToken, clearAuth } = useAppStore();

  useEffect(() => {
    const id = setTimeout(() => setMounted(true), 0);
    return () => clearTimeout(id);
  }, []);

  const handleLogout = async () => {
    try {
      await axios.post(
        `${API_BASE_URL}/auth/logout`,
        {},
        {
          withCredentials: true,
          headers: {
            Authorization: accessToken ? `Bearer ${accessToken}` : "",
          },
        }
      );
    } catch (error) {
      console.error("Failed to logout:", error);
    } finally {
      clearAuthStorage();
      clearAuth();
    }
  };

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="w-full border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md sticky top-0 z-50"
    >
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* LOGO */}
        <Link href="/" className="flex items-center">
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="w-32 h-auto"
          >
            <svg
              viewBox="0 0 280 80"
              xmlns="http://www.w3.org/2000/svg"
              className="w-full h-auto"
            >
              <defs>
                <linearGradient id="epiGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#14b8a6" />
                  <stop offset="100%" stopColor="#06b6d4" />
                </linearGradient>
              </defs>

              {/* Helix/DNA-inspired shape */}
              <g>
                {/* Left spiral */}
                <path
                  d="M 20 40 Q 30 20 40 40 Q 50 60 40 40"
                  stroke="url(#epiGradient)"
                  strokeWidth="3"
                  fill="none"
                  strokeLinecap="round"
                />
                {/* Right spiral */}
                <path
                  d="M 50 40 Q 60 20 70 40 Q 80 60 70 40"
                  stroke="url(#epiGradient)"
                  strokeWidth="3"
                  fill="none"
                  strokeLinecap="round"
                />
                {/* Center connection */}
                <circle cx="45" cy="40" r="4" fill="url(#epiGradient)" />
              </g>

              {/* Text */}
              <text
                x="95"
                y="55"
                fontFamily="Inter, system-ui, sans-serif"
                fontWeight="700"
                fontSize="28"
                className="fill-slate-900 dark:fill-white"
              >
                Epi Meta
              </text>
              <text
                x="95"
                y="72"
                fontFamily="Inter, system-ui, sans-serif"
                fontWeight="600"
                fontSize="14"
                fill="url(#epiGradient)"
              >
                Extracto<tspan className="fill-slate-500 dark:fill-slate-400">r</tspan>
              </text>
            </svg>
          </motion.div>
        </Link>

        {/* NAV LINKS */}
        <div className="flex items-center gap-8">
          <div className="hidden sm:flex items-center gap-8">
            <Link
              href="/results"
              className="text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
            >
              Results
            </Link>
            <Link
              href="/chat"
              className="text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
            >
              Chat
            </Link>
            <Link
              href="/how-to"
              className="text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
            >
              How To
            </Link>
            
            {/* Meta-Analysis Indicator */}
            {metaAnalysis && (
              <div className="text-xs font-medium text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-900/20 px-3 py-1 rounded">
                {metaAnalysis.title}
              </div>
            )}
          </div>

          {/* Create New Project Button */}
          {!metaAnalysis && (
            <Link
              href="/new-meta-analysis"
              className="text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg transition"
            >
              New Project
            </Link>
          )}

          {!authUser && (
            <Link
              href="/auth"
              className="text-sm font-semibold text-slate-700 dark:text-slate-200 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
            >
              Sign in
            </Link>
          )}

          {authUser && (
            <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-300">
              <span className="hidden sm:inline">{authUser.email}</span>
              <button
                onClick={handleLogout}
                className="text-xs font-semibold text-white bg-slate-800 dark:bg-slate-200 dark:text-slate-900 px-3 py-2 rounded-lg hover:opacity-90 transition"
              >
                Logout
              </button>
            </div>
          )}

          {/* Theme Toggle */}
          {mounted && (
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
              aria-label="Toggle theme"
              className="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              {resolvedTheme === "dark" ? "☀️" : "🌙"}
            </motion.button>
          )}
        </div>
      </div>
    </motion.nav>
  );
};
