"use client";

import { Suspense } from "react";
import AuthPageContent from "./AuthPageContent";

export default function AuthPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-pulse text-slate-500">Loading…</div>
        </div>
      }
    >
      <AuthPageContent />
    </Suspense>
  );
}
