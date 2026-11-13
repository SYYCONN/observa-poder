import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata(
  "Senadores",
  "Consulte os senadores importados do Senado Federal, por nome, partido e estado.",
  "/senadores",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
