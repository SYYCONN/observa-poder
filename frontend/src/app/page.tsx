import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { HeroBanner } from "@/components/hero-banner";
import { StructuredData } from "@/components/structured-data";
import { pageMetadata, siteDescription, siteName, siteUrl } from "@/lib/seo";

const title = "Política brasileira com fontes verificáveis";
export const metadata = {
  ...pageMetadata(title, siteDescription, "/"),
  title: { absolute: `${title} | ${siteName}` },
};

const sections = [
  ["Deputados", "Composição da Câmara, partidos, estados e mandatos.", "/deputados"],
  ["Senadores", "Composição do Senado e atuação dos representantes.", "/senadores"],
  ["Governadores", "Consulta em preparação.", "/governadores"],
  ["Partidos", "Consulta em preparação.", "/partidos"],
  ["Projetos", "Propostas, autores, tramitação e fonte oficial.", "/projetos"],
  ["Votações", "Resultados e votos nominais quando disponíveis.", "/votacoes"],
] as const;

export default function Home() {
  return (
    <div className="min-h-screen bg-[#f4f7f8]">
      {siteUrl && (
        <StructuredData
          data={{
            "@context": "https://schema.org",
            "@type": "WebSite",
            name: siteName,
            url: siteUrl.href,
            description: siteDescription,
            inLanguage: "pt-BR",
          }}
        />
      )}
      <SiteHeader />
      <main id="conteudo" tabIndex={-1}>
        <HeroBanner />
        <section className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-20">
          <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-end">
            <div>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.025em] text-[#07152d] sm:text-4xl">
                Consultas do portal
              </h2>
            </div>
            <p className="max-w-2xl text-base leading-7 text-slate-600">
              A cobertura varia por órgão, tipo de registro e período importado.
            </p>
          </div>
          <div className="mt-10 divide-y divide-slate-200 border-y border-slate-200 bg-white">
            {sections.map(([title, description, href]) => (
              <Link
                key={href}
                href={href}
                className="group grid gap-3 px-5 py-5 transition-colors hover:bg-emerald-50/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-700 sm:grid-cols-[180px_1fr_auto] sm:items-center sm:px-7"
              >
                <h3 className="text-xl font-semibold text-[#07152d] group-hover:text-emerald-800">
                  {title}
                </h3>
                <p className="text-sm leading-6 text-slate-600">{description}</p>
                <span className="text-xl text-emerald-700" aria-hidden="true">
                  →
                </span>
              </Link>
            ))}
          </div>
        </section>
        <section className="border-y border-slate-200 bg-white">
          <div className="mx-auto grid max-w-7xl gap-8 px-5 py-12 sm:px-8 md:grid-cols-[1fr_1fr] md:gap-16">
            <div>
              <p className="text-sm font-semibold tracking-[0.08em] text-emerald-700">
                Como ler os dados
              </p>
              <h2 className="mt-3 text-2xl font-semibold tracking-[-0.02em] text-[#07152d]">
                Origem e data dos registros
              </h2>
            </div>
            <div className="space-y-5 text-sm leading-6 text-slate-600">
              <p>
                Na ficha, use o link oficial para conferir o registro original. A data de coleta
                indica quando o portal obteve o dado, e o período de referência indica a que momento
                o registro se refere.
              </p>
              <Link
                href="/fontes-e-privacidade"
                className="inline-flex font-semibold text-emerald-800 underline decoration-emerald-300 underline-offset-4 hover:text-[#07152d]"
              >
                Consultar o catálogo de fontes
              </Link>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
