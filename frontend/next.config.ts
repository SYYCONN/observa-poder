import type { NextConfig } from "next";

const production = process.env.NODE_ENV === "production";
const apiOrigin = new URL(
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
).origin;
// Next hydration uses inline scripts. Nonce-based CSP is a future rendering change.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${production ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: https:",
  "font-src 'self' data:",
  `connect-src 'self' ${apiOrigin}${production ? "" : " ws://localhost:* ws://127.0.0.1:*"}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: { root: process.cwd() },
  poweredByHeader: false,
  async headers() {
    return [{
      source: "/(.*)",
      headers: [
        { key: "Content-Security-Policy", value: csp },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ...(production ? [{ key: "Strict-Transport-Security", value: "max-age=31536000" }] : []),
      ],
    }];
  },
};

export default nextConfig;
