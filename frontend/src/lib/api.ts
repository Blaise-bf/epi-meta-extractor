export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export const buildAuthHeaders = (token?: string | null) => {
  // If no token provided as argument, try to get from localStorage
  let authToken = token;
  if (!authToken && typeof window !== "undefined") {
    authToken = window.localStorage.getItem("epi_access_token");
    console.log("[buildAuthHeaders] Token not provided, loaded from storage:", {
      found: !!authToken,
      tokenStart: authToken ? authToken.substring(0, 20) + "..." : "none",
    });
  }

  if (!authToken) {
    console.log("[buildAuthHeaders] No token available, returning empty headers");
    return {} as Record<string, string>;
  }
  const headers = { Authorization: `Bearer ${authToken}` };
  console.log("[buildAuthHeaders] Built headers with token:", {
    hasAuthorization: !!headers.Authorization,
    authorizationStart: headers.Authorization.substring(0, 30) + "...",
  });
  return headers;
};
