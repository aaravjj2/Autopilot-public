import type { NextConfig } from "next";
import path from "path";

const apexBackend =
  process.env.APEX_BACKEND_URL ||
  process.env.NEXT_PUBLIC_APEX_API_URL ||
  "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // Monorepo: trace files from repo root (autopilot-local + frontend)
  outputFileTracingRoot: path.join(__dirname, "../.."),
  async rewrites() {
    return [
      {
        source: "/apex-api/:path*",
        destination: `${apexBackend.replace(/\/$/, "")}/:path*`,
      },
    ];
  },
};

export default nextConfig;
