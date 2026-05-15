import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  turbopack: {
    root: __dirname,
  },
  // Export static HTML for Render Static Site (free tier)
  output: "export",
  distDir: "dist",
  // Performance optimizations
  experimental: {
    optimizePackageImports: [
      "framer-motion",
      "axios",
      "react-dropzone",
    ],
  },
  // Image optimization (disabled for static export)
  images: {
    unoptimized: true,
  },
  // Compression
  compress: true,
  // Production source maps
  productionBrowserSourceMaps: false,
};

export default nextConfig;
