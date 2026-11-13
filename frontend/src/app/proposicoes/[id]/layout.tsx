import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata(
  "Detalhes da proposição",
  "Ementa, autoria e tramitação de uma proposição, conforme os registros oficiais.",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
