import type { Metadata } from "next";

export const siteName = "Observa Poder";
export const siteDescription =
  "Informações públicas sobre política brasileira, com contexto e fontes verificáveis.";

function configuredSiteUrl(): URL | undefined {
  const value = process.env.SITE_URL?.trim();
  if (!value) return undefined;
  const url = new URL(value);
  if (
    url.protocol !== "https:" ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash ||
    url.hostname === "localhost" ||
    url.hostname.endsWith(".localhost") ||
    url.hostname === "127.0.0.1" ||
    url.hostname === "[::1]"
  ) {
    throw new Error("SITE_URL deve ser a origem HTTPS pública, sem caminho ou credenciais.");
  }
  return url;
}

export const siteUrl = configuredSiteUrl();
// Liberação explícita: o ambiente local e as prévias permanecem fora do índice.
export const indexingEnabled = process.env.SEO_INDEXING_ENABLED === "true" && !!siteUrl;

export function pageMetadata(title: string, description: string, path?: string): Metadata {
  const url = siteUrl && path ? new URL(path, siteUrl).href : undefined;
  const index = indexingEnabled && path !== undefined && sitemapPaths.includes(path);
  return {
    title,
    description,
    alternates: url ? { canonical: url } : undefined,
    robots: { index, follow: indexingEnabled },
    openGraph: {
      type: "website",
      locale: "pt_BR",
      siteName,
      title: `${title} | ${siteName}`,
      description,
      ...(url ? { url } : {}),
    },
    twitter: { card: "summary", title: `${title} | ${siteName}`, description },
  };
}

// Não anunciar placeholders nem registros carregados apenas depois da hidratação.
export const sitemapPaths: readonly string[] = ["/", "/metodologia", "/fontes-e-privacidade"];
