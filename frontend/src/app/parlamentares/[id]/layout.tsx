import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata(
  "Perfil parlamentar",
  "Perfil e registros públicos de um parlamentar, com referência à fonte oficial.",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
