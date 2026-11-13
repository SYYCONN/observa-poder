import type { MetadataRoute } from "next";
import { indexingEnabled, siteUrl } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    // Permite ler o noindex nas páginas. Robots.txt não é controle de acesso.
    rules: { userAgent: "*", allow: "/" },
    ...(indexingEnabled && siteUrl ? { sitemap: new URL("/sitemap.xml", siteUrl).href } : {}),
  };
}
