import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  /* config options here */
  turbopack: {
    // Set root to the current directory (frontend/incuera-frontend)
    // This tells Turbopack where the project root is to avoid lockfile warnings
    root: path.resolve(process.cwd()),
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
