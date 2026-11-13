import { pageMetadata, siteDescription, siteName } from "@/lib/seo";
import { SearchPageContent } from "@/components/search-page-content";

const title = "Pesquisa no portal";

export const metadata = {
  ...pageMetadata(title, siteDescription, "/pesquisa"),
  title: { absolute: `${title} | ${siteName}` },
};

export default function PesquisaPage() {
  return <SearchPageContent />;
}
