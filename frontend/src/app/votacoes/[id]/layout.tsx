import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata(
  "Detalhes da votação",
  "Resultado e votos publicados de uma votação, conforme a fonte oficial.",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
