/**
 * The frontend is also the API gateway: the browser only ever calls same-origin /api/*, and these rewrites
 * forward each path to the service that owns it. Benefits: no CORS, one public URL, and service URLs can change
 * without a frontend change. With a single backend (SERVICE=all, local dev) every *_SERVICE_URL falls back to
 * API_URL.
 */
const base = (process.env.API_URL || "http://localhost:8000").replace(/\/$/, "");
const svc = (name) => (process.env[`${name}_SERVICE_URL`] || base).replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [
      { source: "/api/auth/:path*", destination: `${svc("AUTH")}/auth/:path*` },
      { source: "/api/me/:path*", destination: `${svc("AUTH")}/me/:path*` },
      { source: "/api/resume", destination: `${svc("RESUME")}/resume` },
      { source: "/api/resume/:path*", destination: `${svc("RESUME")}/resume/:path*` },
      { source: "/api/interview/:path*", destination: `${svc("INTERVIEW")}/interview/:path*` },
      { source: "/api/:path*", destination: `${svc("JOBS")}/:path*` },
    ];
  },
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        // microphone=(self): the mock interview records answers in the browser
        { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self)" },
      ],
    }];
  },
};
export default nextConfig;
