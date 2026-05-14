"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { extractErrorMessage } from "@/lib/errors";
import { useAppStore } from "@/store/useAppStore";
import { saveAuthToStorage } from "@/lib/auth";
import { Spinner } from "@/components/ui/Skeleton";

export default function AuthPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const setAuth = useAppStore((s) => s.setAuth);

  const token = useMemo(() => searchParams.get("token"), [searchParams]);
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [devLink, setDevLink] = useState<string | null>(null);

  // Verify magic link token
  useEffect(() => {
    if (!token) return;

    setLoading(true);
    setStatus("Verifying your sign-in link...");
    setError(null);

    api.auth
      .verify(token)
      .then(({ data }) => {
        setAuth(data.user, data.access_token);
        saveAuthToStorage(data.access_token, data.user);
        setStatus("Signed in! Redirecting...");
        setTimeout(() => router.push("/"), 600);
      })
      .catch(() => {
        setError("That link is invalid or expired. Request a new one below.");
        setStatus(null);
      })
      .finally(() => setLoading(false));
  }, [token, router, setAuth]);

  const handleRequestLink = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const normalizedEmail = email.trim();
      if (!normalizedEmail) {
        setError("Please enter a valid email address.");
        return;
      }

      setLoading(true);
      setError(null);
      setStatus(null);
      setDevLink(null);

      try {
        const { data } = await api.auth.requestLink(normalizedEmail);
        if (data?.magic_link) setDevLink(data.magic_link);
        setStatus("Check your email for a sign-in link.");
      } catch (err: unknown) {
        setError(extractErrorMessage(err, "Could not send link. Please try again."));
      } finally {
        setLoading(false);
      }
    },
    [email]
  );

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#e0f2fe,#f8fafc_50%,#f1f5f9)] dark:bg-[radial-gradient(circle_at_top,#1e293b,#0f172a_50%,#020617)] flex items-center justify-center px-6 py-12">
      <div className="relative w-full max-w-xl">
        <div className="absolute -top-10 -left-8 h-24 w-24 rounded-full bg-teal-200/60 dark:bg-teal-900/40 blur-2xl" />
        <div className="absolute -bottom-12 right-6 h-32 w-32 rounded-full bg-sky-200/60 dark:bg-sky-900/40 blur-2xl" />

        <div className="relative overflow-hidden rounded-3xl border border-slate-200 dark:border-slate-700 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm p-8 shadow-xl">
          <div className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-500 dark:text-teal-400">
              Secure Access
            </p>
            <h1 className="mt-2 text-3xl font-bold text-slate-900 dark:text-slate-100">
              Sign in to track your meta-analyses
            </h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              We use passwordless magic links. Enter your email and we will send
              a secure link to your inbox.
            </p>
          </div>

          <form onSubmit={handleRequestLink} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="text-sm font-semibold text-slate-700 dark:text-slate-300"
              >
                Email address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@institute.org"
                className="mt-2 w-full rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-4 py-3 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 shadow-sm focus:border-teal-400 dark:focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-200 dark:focus:ring-teal-800 transition-colors"
                disabled={loading}
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading || !email.trim()}
              className="w-full rounded-xl bg-slate-900 dark:bg-slate-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 dark:hover:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-70 flex items-center justify-center gap-2"
            >
              {loading && <Spinner className="w-4 h-4" />}
              {loading ? "Sending..." : "Send sign-in link"}
            </button>
          </form>

          {(status || error) && (
            <div
              className={`mt-6 rounded-2xl border px-4 py-3 text-sm ${
                error
                  ? "border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-400"
                  : "border-teal-200 dark:border-teal-800 bg-teal-50 dark:bg-teal-900/20 text-teal-700 dark:text-teal-400"
              }`}
            >
              {error || status}
            </div>
          )}

          {devLink && (
            <div className="mt-4 rounded-2xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 px-4 py-3 text-xs text-amber-800 dark:text-amber-400">
              <div className="font-semibold uppercase tracking-[0.12em]">
                Dev Link
              </div>
              <a
                href={devLink}
                className="mt-2 block break-all text-sm font-medium text-amber-900 dark:text-amber-300 hover:underline"
              >
                {devLink}
              </a>
            </div>
          )}

          <div className="mt-8 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Links expire after 15 minutes.</span>
            <span>No passwords stored.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
