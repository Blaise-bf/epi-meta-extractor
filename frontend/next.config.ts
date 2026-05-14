import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  turbopack: {
    root: __dirname,
  },
  // Required for Docker multi-stage build (outputs standalone server.js)
  output: "standalone",
  // Performance optimizations
  experimental: {
    optimizePackageImports: [
      "framer-motion",
      "axios",
      "react-dropzone",
    ],
  },
  // Image optimization
  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [],
  },
  // Compression
  compress: true,
  // Production source maps (disable for smaller builds)
  productionBrowserSourceMaps: false,
};

export default nextConfig;
