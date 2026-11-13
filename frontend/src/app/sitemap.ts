import type { MetadataRoute } from "next";
import { indexingEnabled, siteUrl, sitemapPaths } from "@/lib/seo";

export default function sitemap(): MetadataRoute.Sitemap {
  if (!indexingEnabled || !siteUrl) return [];
  return sitemapPaths.map((path) => ({ url: new URL(path, siteUrl).href }));
}
