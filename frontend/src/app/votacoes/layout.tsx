import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata(
  "Votações",
  "Consulte resultados e votos nominais importados da Câmara e do Senado, quando publicados pela fonte.",
  "/votacoes",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
