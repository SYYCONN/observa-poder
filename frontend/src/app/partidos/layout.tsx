import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata(
  "Partidos políticos",
  "A consulta de partidos e seus representantes está em preparação.",
  "/partidos",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
