"use client";

import Link from "next/link";
import { motion } from "framer-motion";

export const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <motion.footer
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="w-full border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 mt-20"
    >
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand */}
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
              Epi Meta Extractor
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
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
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
                >
                  Home
                </Link>
              </li>
              <li>
                <Link
                  href="/results"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
                >
                  Results
                </Link>
              </li>
              <li>
                <Link
                  href="/chat"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
                >
                  Chat
                </Link>
              </li>
              <li>
                <Link
                  href="/how-to"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
                >
                  How To
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
                <a
                  href="#"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
                >
                  Documentation
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
                >
                  API Reference
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
                >
                  Support
                </a>
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
                <a
                  href="#"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
                >
                  Privacy
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
                >
                  Terms
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-sm text-slate-600 dark:text-slate-400 hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
                >
                  License
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-slate-200 dark:border-slate-800 pt-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-slate-600 dark:text-slate-400">
            <p>© {currentYear} Epi Meta Extractor. All rights reserved.</p>
            <div className="flex gap-6">
              <a
                href="#"
                className="hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
              >
                Twitter
              </a>
              <a
                href="#"
                className="hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
              >
                GitHub
              </a>
              <a
                href="#"
                className="hover:text-teal-500 dark:hover:text-teal-400 transition-colors"
              >
                LinkedIn
              </a>
            </div>
          </div>
        </div>
      </div>
    </motion.footer>
  );
};
