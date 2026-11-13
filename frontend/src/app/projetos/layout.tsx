import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata(
  "Projetos e proposições",
  "Consulte proposições da Câmara e do Senado, com ementa, autoria, tramitação e fonte oficial.",
  "/projetos",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
