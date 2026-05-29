import type { NextConfig } from "next";

const apexBackend =
  process.env.APEX_BACKEND_URL ||
  process.env.NEXT_PUBLIC_APEX_API_URL ||
  "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
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
