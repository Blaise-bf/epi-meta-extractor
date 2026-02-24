"use client";

"use client";

import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ThemeProvider } from "next-themes";
import { Roboto } from "next/font/google";
import { useEffect } from "react";
import { useAppStore } from "@/store/useAppStore";
import { loadAuthFromStorage, saveAuthToStorage } from "@/lib/auth";
import axios from "axios";
import { API_BASE_URL } from "@/lib/api";

const roboto = Roboto({
  subsets: ["latin"],
  weight: ["300", "400", "500", "700"],
  variable: "--font-roboto",
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { authUser, accessToken, setAuth, setAuthChecked } = useAppStore();

  useEffect(() => {
    const initAuth = async () => {
      console.log("[Layout] useEffect running");
      
      // First, try to load from storage (synchronous)
      const { token, user } = loadAuthFromStorage();
      console.log("[Layout] Loaded from storage:", { 
        hasToken: !!token,
        hasUser: !!user,
        token: token ? token.substring(0, 20) + "..." : null,
      });
      
      if (token && user) {
        console.log("[Layout] Setting auth from storage");
        setAuth(user, token);
        setAuthChecked(true);
        return;
      }

      // If no stored auth, try to refresh from server
      try {
        console.log("[Layout] No stored auth, attempting to refresh session");
        const response = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );
        const { access_token, user: refreshedUser } = response.data;
        console.log("[Layout] Refresh successful");
        setAuth(refreshedUser, access_token);
        saveAuthToStorage(access_token, refreshedUser);
      } catch (error) {
        console.log("[Layout] Refresh failed or not available:", error);
        // Silent if refresh not available
      } finally {
        console.log("[Layout] Marking auth as checked");
        setAuthChecked(true);
      }
    };

    // Only run once on mount
    initAuth();
  }, [setAuth, setAuthChecked]);

  return (
    <html lang="en" suppressHydrationWarning className={roboto.variable}>
      <body
        suppressHydrationWarning
        className="bg-white dark:bg-slate-950 text-slate-900 dark:text-white min-h-screen transition-colors flex flex-col font-roboto"
      >
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <Navbar />
          <main className="max-w-6xl mx-auto px-6 py-12 grow w-full">
            {children}
          </main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
