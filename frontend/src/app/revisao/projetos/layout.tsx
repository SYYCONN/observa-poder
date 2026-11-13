import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Monitor da automação cidadã · acesso restrito",
  robots: { index: false, follow: false },
};

export default function AutomationMonitorLayout({ children }: { children: React.ReactNode }) {
  return children;
}
