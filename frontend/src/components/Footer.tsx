"use client";

import { memo } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";

export const Footer = memo(function Footer() {
  const currentYear = new Date().getFullYear();
  const reduceMotion = useReducedMotion();

  return (
    <motion.footer
      initial={reduceMotion ? false : { y: 20, opacity: 0 }}
      animate={reduceMotion ? undefined : { y: 0, opacity: 1 }}
      transition={reduceMotion ? undefined : { duration: 0.5, delay: 0.2 }}
      className="w-full border-t border-cyan-100 dark:border-slate-800 bg-white/60 dark:bg-slate-950/60 backdrop-blur mt-20"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand */}
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4 text-lg">
              Epi Meta Extractor
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 max-w-xs">
              Automated epidemiologic meta-extraction for research studies.
            </p>
          </div>

          {/* Navigation */}
          <div>
            <h4 className="font-semibold text-slate-900 dark:text-white mb-4 text-sm">
              Navigation
            </h4>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-cyan-700 dark:hover:text-cyan-300 transition-colors"
                >
                  Home
                </Link>
              </li>
              <li>
                <Link
                  href="/results"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-cyan-700 dark:hover:text-cyan-300 transition-colors"
                >
                  Results
                </Link>
              </li>
              <li>
                <Link
                  href="/new-meta-analysis"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-cyan-700 dark:hover:text-cyan-300 transition-colors"
                >
                  New Project
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="font-semibold text-slate-900 dark:text-white mb-4 text-sm">
              Resources
            </h4>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/how-to"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-cyan-700 dark:hover:text-cyan-300 transition-colors"
                >
                  How To
                </Link>
              </li>
              <li>
                <Link
                  href="/chat"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-cyan-700 dark:hover:text-cyan-300 transition-colors"
                >
                  Chat
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="font-semibold text-slate-900 dark:text-white mb-4 text-sm">
              Legal
            </h4>
            <ul className="space-y-2">
              <li>
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  Privacy Policy
                </span>
              </li>
              <li>
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  Terms of Service
                </span>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-slate-200 dark:border-slate-800 pt-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            © {currentYear} Epi Meta Extractor. All rights reserved.
          </p>
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Built with Next.js, FastAPI, and GROBID
          </p>
        </div>
      </div>
    </motion.footer>
  );
});
