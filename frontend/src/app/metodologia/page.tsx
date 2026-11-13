import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { StructuredData } from "@/components/structured-data";
import { pageMetadata, siteName, siteUrl } from "@/lib/seo";

const title = "Metodologia e limites dos dados";
const description =
  "Como consultar a origem, a data de coleta e as limitações dos registros publicados no Observa Poder.";
export const metadata = pageMetadata(title, description, "/metodologia");

export default function MethodologyPage() {
  return (
    <div className="min-h-screen bg-[var(--paper)]">
      <SiteHeader />
      {siteUrl && (
        <StructuredData
          data={{
            "@context": "https://schema.org",
            "@type": "AboutPage",
            name: title,
            description,
            url: new URL("/metodologia", siteUrl).href,
            inLanguage: "pt-BR",
            isPartOf: { "@type": "WebSite", name: siteName, url: siteUrl.href },
          }}
        />
      )}
      <main
        id="conteudo"
        tabIndex={-1}
        className="mx-auto max-w-3xl space-y-8 px-5 py-12 leading-7 sm:px-8"
      >
        <header>
          <h1 className="text-3xl font-semibold tracking-tight text-[#07152d] sm:text-4xl">
            {title}
          </h1>
          <p className="mt-5 text-lg text-slate-600">
            O portal organiza registros públicos para facilitar a consulta. A fonte oficial indicada
            em cada registro é a referência para conferir seu conteúdo.
          </p>
        </header>
        <section aria-labelledby="origem">
          <h2 id="origem" className="text-2xl font-semibold">
            De onde vêm as informações?
          </h2>
          <p className="mt-3">
            As consultas legislativas reúnem dados importados da Câmara dos Deputados e do Senado
            Federal. Use o link de fonte oficial na ficha para conferir o registro original. Se uma
            seção estiver em preparação, isso não significa que seus dados já foram coletados.
          </p>
        </section>
        <section aria-labelledby="atualizacao">
          <h2 id="atualizacao" className="text-2xl font-semibold">
            Os dados são atualizados em tempo real?
          </h2>
          <p className="mt-3">
            Não. A coleta ocorre em processos separados da consulta ao portal. A data de coleta,
            quando exibida, informa quando o registro foi obtido; ela não substitui a data de
            apresentação de uma proposta ou de realização de uma votação. Alterações na fonte podem
            ainda não aparecer aqui.
          </p>
        </section>
        <section aria-labelledby="ausencia">
          <h2 id="ausencia" className="text-2xl font-semibold">
            Como interpretar um dado ausente?
          </h2>
          <p className="mt-3">
            Uma lista vazia ou um campo não informado pode refletir limites da importação ou da
            publicação da fonte. Não permite concluir que um parlamentar faltou, que não houve gasto
            ou que uma proposição não tem autoria. Erros de consulta também não são evidência de
            ausência de atividade.
          </p>
        </section>
        <section aria-labelledby="votos">
          <h2 id="votos" className="text-2xl font-semibold">
            O resultado de uma votação mostra cada voto?
          </h2>
          <p className="mt-3">
            O portal apresenta o resultado e os registros nominais disponíveis separadamente. Não
            atribui voto individual a partir do resultado agregado, do partido ou de um registro
            ausente. Para conferir o contexto da decisão, consulte a votação e as proposições
            relacionadas na fonte indicada.
          </p>
        </section>
        <section aria-labelledby="ementa">
          <h2 id="ementa" className="text-2xl font-semibold">
            A ementa substitui o texto integral?
          </h2>
          <p className="mt-3">
            Não. A ementa é apresentada como resumo da matéria. Consulte o texto integral, as
            emendas, os pareceres e a tramitação na fonte oficial antes de tirar conclusões sobre o
            alcance de uma proposta.
          </p>
        </section>
        <section aria-labelledby="citacao">
          <h2 id="citacao" className="text-2xl font-semibold">
            Como citar um registro do portal?
          </h2>
          <p className="mt-3">
            Informe o órgão de origem, o identificador do registro e o link oficial. Inclua a data
            do evento ou o período de referência e a data da coleta exibida na ficha. Ao citar uma
            explicação do portal, identifique-a como explicação e indique o endereço da ficha.
          </p>
        </section>
        <nav
          aria-label="Consultas relacionadas"
          className="flex flex-wrap gap-6 border-t border-slate-200 pt-6 font-semibold text-emerald-800 underline underline-offset-4"
        >
          <Link href="/fontes-e-privacidade">Catálogo de fontes oficiais</Link>
          <Link href="/projetos">Consultar proposições</Link>
          <Link href="/votacoes">Consultar votações</Link>
        </nav>
      </main>
      <SiteFooter />
    </div>
  );
}
