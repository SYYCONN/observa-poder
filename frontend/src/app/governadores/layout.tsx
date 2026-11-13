import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata(
  "Governadores",
  "A consulta de governadores está em preparação. Confira o estágio de disponibilidade dos dados.",
  "/governadores",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
