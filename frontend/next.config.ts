import type { NextConfig } from "next";

// Inside Docker: backend:8000 | Outside Docker: localhost:8001
const BACKEND_URL = process.env.INTERNAL_API_URL || 'http://127.0.0.1:8001';

const nextConfig: NextConfig = {
  turbopack: {
    // Evita inferencias incorrectas de root cuando existen lockfiles fuera de /frontend.
    root: __dirname,
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${BACKEND_URL}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
