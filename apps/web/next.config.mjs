/** @type {import('next').NextConfig} */
const nextConfig = {
  // The FastAPI backend ships no CORS middleware (flagged for Phase 6), so
  // the browser talks to same-origin /api/v1 and Next proxies it through.
  async rewrites() {
    const target = process.env.API_PROXY_TARGET ?? "http://localhost:8000";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${target}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
