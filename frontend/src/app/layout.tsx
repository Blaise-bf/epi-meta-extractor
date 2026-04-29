"use client";

import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ThemeProvider } from "next-themes";
import { Space_Grotesk } from "next/font/google";
import { useEffect } from "react";
import { useAppStore } from "@/store/useAppStore";
import { loadAuthFromStorage, saveAuthToStorage } from "@/lib/auth";
import { api } from "@/lib/api";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-space-grotesk",
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const setAuth = useAppStore((s) => s.setAuth);
  const setAuthChecked = useAppStore((s) => s.setAuthChecked);

  useEffect(() => {
    const initAuth = async () => {
      // First, try to load from storage (synchronous)
      const { token, user } = loadAuthFromStorage();

      if (token && user) {
        setAuth(user, token);
        setAuthChecked(true);
        return;
      }

      // If no stored auth, try to refresh from server
      try {
        const response = await api.auth.refresh();
        const { access_token, user: refreshedUser } = response.data;
        setAuth(refreshedUser, access_token);
        saveAuthToStorage(access_token, refreshedUser);
      } catch {
        // Silent if refresh not available
      } finally {
        setAuthChecked(true);
      }
    };

    initAuth();
  }, [setAuth, setAuthChecked]);

  return (
    <html lang="en" suppressHydrationWarning className={spaceGrotesk.variable}>
      <body
        suppressHydrationWarning
        className="text-slate-900 dark:text-white min-h-screen transition-colors flex flex-col"
      >
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <ErrorBoundary>
            <Navbar />
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 grow w-full">
              {children}
            </main>
            <Footer />
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  );
}
