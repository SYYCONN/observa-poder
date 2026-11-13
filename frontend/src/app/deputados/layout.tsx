import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata(
  "Deputados federais",
  "Consulte os deputados federais importados da Câmara dos Deputados, por nome, partido e estado.",
  "/deputados",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
