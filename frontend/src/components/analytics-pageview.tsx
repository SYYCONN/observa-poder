"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

const pages = new Set([
  "/",
  "/deputados",
  "/senadores",
  "/governadores",
  "/partidos",
  "/projetos",
  "/votacoes",
]);

export function AnalyticsPageview() {
  const pathname = usePathname();
  const lastRoute = useRef<string | null>(null);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_ANALYTICS_ENABLED !== "true") return;
    if (
      navigator.doNotTrack === "1" ||
      (navigator as Navigator & { globalPrivacyControl?: boolean }).globalPrivacyControl
    )
      return;
    const route = pages.has(pathname)
      ? pathname
      : /^\/(parlamentares|proposicoes|votacoes)\/[^/]+$/.test(pathname)
        ? `/${pathname.split("/")[1]}/[id]`
        : null;
    if (!route) {
      lastRoute.current = null;
      return;
    }
    // Compare the path locally, but only transmit the fixed route template.
    if (lastRoute.current === pathname) return;
    lastRoute.current = pathname;
    const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    void fetch(`${api}/analytics/pageviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ route }),
      credentials: "omit",
      referrerPolicy: "no-referrer",
      keepalive: true,
    }).catch(() => undefined);
  }, [pathname]);

  return null;
}
