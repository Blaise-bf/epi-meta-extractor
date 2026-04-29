"use client";

import { useEffect, useState } from "react";

interface SkeletonProps {
  className?: string;
}

export const Skeleton = ({ className = "" }: SkeletonProps) => (
  <div
    className={`animate-pulse bg-slate-200 dark:bg-slate-700 rounded ${className}`}
  />
);

export const CardSkeleton = () => (
  <div className="surface-card rounded-2xl p-5 sm:p-6 space-y-4">
    <Skeleton className="h-6 w-3/4" />
    <Skeleton className="h-4 w-1/2" />
    <div className="space-y-2 pt-2">
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-4 w-4/6" />
    </div>
  </div>
);

export const ProjectCardSkeleton = () => (
  <div className="w-full text-left p-4 border border-slate-200 dark:border-slate-700 bg-white/90 dark:bg-slate-900/70 rounded-2xl">
    <Skeleton className="h-5 w-3/4 mb-2" />
    <Skeleton className="h-4 w-1/2 mb-1" />
    <Skeleton className="h-3 w-1/3" />
  </div>
);

export const StudyCardSkeleton = () => (
  <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-6 shadow-sm">
    <div className="flex justify-between items-start mb-4">
      <Skeleton className="h-6 w-2/3" />
      <Skeleton className="h-5 w-16" />
    </div>
    <Skeleton className="h-4 w-1/3 mb-4" />
    <div className="grid grid-cols-2 gap-4">
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-full" />
    </div>
  </div>
);

export const Spinner = ({ className = "" }: SkeletonProps) => (
  <svg
    className={`animate-spin text-cyan-600 dark:text-cyan-400 ${className}`}
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
  >
    <circle
      className="opacity-25"
      cx="12"
      cy="12"
      r="10"
      stroke="currentColor"
      strokeWidth="4"
    />
    <path
      className="opacity-75"
      fill="currentColor"
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    />
  </svg>
);

export const FullPageLoader = ({ message = "Loading..." }: { message?: string }) => (
  <div className="min-h-[50vh] flex flex-col items-center justify-center gap-4">
    <Spinner className="w-10 h-10" />
    <p className="text-slate-600 dark:text-slate-400 text-sm">{message}</p>
  </div>
);

export const DelayedLoader = ({
  delay = 300,
  message = "Loading...",
}: {
  delay?: number;
  message?: string;
}) => {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShow(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  if (!show) return null;
  return <FullPageLoader message={message} />;
};
