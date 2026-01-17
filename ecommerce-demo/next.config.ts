import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  /* config options here */
  turbopack: {
    // Set root to parent directory to include both ecommerce-demo and packages/sdk
    // This allows Turbopack to resolve the local file dependency
    root: path.resolve(process.cwd(), '..'),
  },
  // Transpile the local SDK package - required for local file dependencies
  transpilePackages: ['@incuera/sdk'],
  // Webpack fallback configuration (for non-Turbopack builds)
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@incuera/sdk': path.resolve(process.cwd(), '../packages/sdk'),
    };
    return config;
  },
};

export default nextConfig;
