"use client";

import { memo, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { motion, useReducedMotion } from "framer-motion";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import { clearAuthStorage } from "@/lib/auth";

// ---------------------------------------------------------------------------
// Logo Component (extracted to prevent re-renders)
// ---------------------------------------------------------------------------

const Logo = memo(function Logo() {
  return (
    <Link href="/" className="flex items-center gap-3">
      <motion.div
        whileHover={{ scale: 1.05 }}
        className="w-32 sm:w-36 h-auto"
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
          <g>
            <path
              d="M 20 40 Q 30 20 40 40 Q 50 60 40 40"
              stroke="url(#epiGradient)"
              strokeWidth="3"
              fill="none"
              strokeLinecap="round"
            />
            <path
              d="M 50 40 Q 60 20 70 40 Q 80 60 70 40"
              stroke="url(#epiGradient)"
              strokeWidth="3"
              fill="none"
              strokeLinecap="round"
            />
            <circle cx="45" cy="40" r="4" fill="url(#epiGradient)" />
          </g>
          <text
            x="95"
            y="55"
            fontFamily="var(--font-space-grotesk), Segoe UI, sans-serif"
            fontWeight="700"
            fontSize="28"
            className="fill-slate-900 dark:fill-white"
          >
            Epi Meta
          </text>
          <text
            x="95"
            y="72"
            fontFamily="var(--font-space-grotesk), Segoe UI, sans-serif"
            fontWeight="600"
            fontSize="14"
            fill="url(#epiGradient)"
          >
            Extracto
            <tspan className="fill-slate-500 dark:fill-slate-400">r</tspan>
          </text>
        </svg>
      </motion.div>
    </Link>
  );
});

// ---------------------------------------------------------------------------
// Nav Links
// ---------------------------------------------------------------------------

const NavLinks = memo(function NavLinks({
  metaAnalysis,
}: {
  metaAnalysis: { title: string } | null;
}) {
  return (
    <div className="hidden md:flex items-center gap-2 rounded-full border border-cyan-100 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 px-2 py-1">
      <Link
        href="/results"
        className="text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-cyan-700 dark:hover:text-cyan-300 transition-colors px-3 py-1.5 rounded-full hover:bg-cyan-50 dark:hover:bg-slate-800"
      >
        Results
      </Link>
      <Link
        href="/chat"
        className="text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-cyan-700 dark:hover:text-cyan-300 transition-colors px-3 py-1.5 rounded-full hover:bg-cyan-50 dark:hover:bg-slate-800"
      >
        Chat
      </Link>
      <Link
        href="/how-to"
        className="text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-cyan-700 dark:hover:text-cyan-300 transition-colors px-3 py-1.5 rounded-full hover:bg-cyan-50 dark:hover:bg-slate-800"
      >
        How To
      </Link>
      {metaAnalysis && (
        <div className="text-xs font-semibold text-cyan-700 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-900/20 px-3 py-1.5 rounded-full max-w-48 truncate">
          {metaAnalysis.title}
        </div>
      )}
    </div>
  );
});

// ---------------------------------------------------------------------------
// Theme Toggle
// ---------------------------------------------------------------------------

const ThemeToggle = memo(function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const reduceMotion = useReducedMotion();

  return (
    <motion.button
      whileHover={reduceMotion ? undefined : { scale: 1.1 }}
      whileTap={reduceMotion ? undefined : { scale: 0.95 }}
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      aria-label="Toggle theme"
      className="px-3 py-2 rounded-full border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-xs font-semibold"
    >
      {resolvedTheme === "dark" ? "Light" : "Dark"}
    </motion.button>
  );
});

// ---------------------------------------------------------------------------
// Mobile Menu
// ---------------------------------------------------------------------------

const MobileMenu = memo(function MobileMenu({
  open,
  onClose,
  metaAnalysis,
  authUser,
  onLogout,
}: {
  open: boolean;
  onClose: () => void;
  metaAnalysis: { title: string } | null;
  authUser: { email: string } | null;
  onLogout: () => void;
}) {
  if (!open) return null;

  return (
    <div className="md:hidden border-t border-cyan-100 dark:border-slate-800 px-4 pb-4 pt-3 bg-white/90 dark:bg-slate-950/90">
      <div className="flex flex-col gap-2">
        {metaAnalysis && (
          <div className="text-xs font-semibold text-cyan-700 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-900/20 px-3 py-2 rounded-xl">
            Active: {metaAnalysis.title}
          </div>
        )}
        <Link
          href="/results"
          onClick={onClose}
          className="px-3 py-2 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-cyan-50 dark:hover:bg-slate-800"
        >
          Results
        </Link>
        <Link
          href="/chat"
          onClick={onClose}
          className="px-3 py-2 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-cyan-50 dark:hover:bg-slate-800"
        >
          Chat
        </Link>
        <Link
          href="/how-to"
          onClick={onClose}
          className="px-3 py-2 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-cyan-50 dark:hover:bg-slate-800"
        >
          How To
        </Link>
        {!metaAnalysis && (
          <Link
            href="/new-meta-analysis"
            onClick={onClose}
            className="mt-1 px-3 py-2 rounded-xl text-sm font-semibold text-white bg-linear-to-r from-cyan-600 to-teal-600"
          >
            New Project
          </Link>
        )}
        {!authUser && (
          <Link
            href="/auth"
            onClick={onClose}
            className="px-3 py-2 rounded-xl text-sm font-semibold text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-700"
          >
            Sign in
          </Link>
        )}
        {authUser && (
          <div className="mt-1 flex items-center justify-between gap-3 px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-900">
            <span className="text-xs text-slate-600 dark:text-slate-300 truncate">
              {authUser.email}
            </span>
            <button
              onClick={onLogout}
              className="text-xs font-semibold text-white bg-slate-800 dark:bg-slate-200 dark:text-slate-900 px-3 py-1.5 rounded-full"
            >
              Logout
            </button>
          </div>
        )}
      </div>
    </div>
  );
});

// ---------------------------------------------------------------------------
// Main Navbar
// ---------------------------------------------------------------------------

export const Navbar = memo(function Navbar() {
  const metaAnalysis = useAppStore((s) => s.metaAnalysis);
  const authUser = useAppStore((s) => s.authUser);
  const accessToken = useAppStore((s) => s.accessToken);
  const clearAuth = useAppStore((s) => s.clearAuth);

  const [mounted, setMounted] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await api.auth.logout();
    } catch {
      // Silent fail
    } finally {
      clearAuthStorage();
      clearAuth();
      setMobileOpen(false);
    }
  }, [clearAuth]);

  return (
    <motion.nav
      initial={reduceMotion ? false : { y: -20, opacity: 0 }}
      animate={reduceMotion ? undefined : { y: 0, opacity: 1 }}
      transition={reduceMotion ? undefined : { duration: 0.5 }}
      className="w-full border-b border-cyan-100/80 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur-xl sticky top-0 z-50"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between gap-4">
        <Logo />

        <div className="flex items-center gap-3 sm:gap-5">
          <NavLinks metaAnalysis={metaAnalysis} />

          {!metaAnalysis && (
            <Link
              href="/new-meta-analysis"
              className="hidden sm:inline-flex text-sm font-semibold text-white bg-linear-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 px-4 py-2 rounded-full transition shadow-sm"
            >
              New Project
            </Link>
          )}

          {!authUser && (
            <Link
              href="/auth"
              className="text-sm font-semibold text-slate-700 dark:text-slate-200 hover:text-cyan-700 dark:hover:text-cyan-300 transition-colors"
            >
              Sign in
            </Link>
          )}

          {authUser && (
            <div className="hidden lg:flex items-center gap-3 text-sm text-slate-600 dark:text-slate-300">
              <span className="max-w-48 truncate">{authUser.email}</span>
              <button
                onClick={handleLogout}
                className="text-xs font-semibold text-white bg-slate-800 dark:bg-slate-200 dark:text-slate-900 px-3 py-2 rounded-full hover:opacity-90 transition"
              >
                Logout
              </button>
            </div>
          )}

          {mounted && <ThemeToggle />}

          <button
            type="button"
            aria-label="Toggle mobile navigation"
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((v) => !v)}
            className="md:hidden px-3 py-2 rounded-full border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            {mobileOpen ? "Close" : "Menu"}
          </button>
        </div>
      </div>

      <MobileMenu
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        metaAnalysis={metaAnalysis}
        authUser={authUser}
        onLogout={handleLogout}
      />
    </motion.nav>
  );
});
