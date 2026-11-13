import type { Metadata } from "next";
import { siteDescription, siteName, siteUrl } from "@/lib/seo";
import "./globals.css";
import { AnalyticsPageview } from "@/components/analytics-pageview";

export const metadata: Metadata = {
  metadataBase: siteUrl,
  title: { default: siteName, template: `%s | ${siteName}` },
  description: siteDescription,
  applicationName: siteName,
  robots: { index: false, follow: false },
  icons: { icon: "/brand/de-olho-na-politica.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>
        <a href="#conteudo" className="skip-link">
          Pular para o conteúdo
        </a>
        <AnalyticsPageview />
        {children}
      </body>
    </html>
  );
}
