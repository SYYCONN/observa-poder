import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Analytics · acesso restrito",
  robots: { index: false, follow: false },
};

export default function AnalyticsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
