import Link from "next/link";
import { pageMetadata } from "@/lib/seo";
import { SiteFooter, SiteHeader } from "@/components/site-header";

const title = "Fontes, limites e privacidade";
const privacyContact = process.env.NEXT_PUBLIC_PRIVACY_CONTACT?.trim();
const hasPrivacyContact = privacyContact && /^[\w.+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i.test(privacyContact);
export const metadata = pageMetadata(
  title,
  "Consulte as fontes oficiais, as datas de coleta, os limites de cobertura e os cuidados com dados pessoais no portal.",
  "/fontes-e-privacidade",
);

const sources = [
  {
    name: "Câmara dos Deputados",
    href: "https://dadosabertos.camara.leg.br/swagger/api.html",
    coverage:
      "Deputados, proposições, tramitações e votações; despesas da cota, remuneração e equipes a partir dos arquivos e consultas de transparência da Câmara.",
    limits:
      "A cobertura varia por conjunto e período importado. Filiação atual não reconstrói o partido no dia de um voto; remuneração e equipe dependem da competência consultada.",
  },
  {
    name: "Senado Federal",
    href: "https://legis.senado.leg.br/dadosabertos/api-docs/swagger-ui/index.html",
    coverage:
      "Senadores, matérias legislativas, tramitações e votações disponíveis nos coletores do Senado.",
    limits:
      "Os modelos e identificadores diferem dos da Câmara. Uma seção disponível para deputados não implica a mesma cobertura para senadores.",
  },
  {
    name: "Portal da Transparência",
    href: "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares",
    coverage:
      "Emendas parlamentares, com exercício, código oficial e valores empenhados, liquidados e pagos, conforme o recorte importado.",
    limits:
      "Autoria não significa recebimento pessoal. Empenho, liquidação e pagamento são etapas distintas; valores ausentes não devem ser tratados como zero.",
  },
  {
    name: "Tribunal Superior Eleitoral",
    href: "https://dadosabertos.tse.jus.br/",
    coverage:
      "Resultados eleitorais por eleição, cargo, UF, turno e identificador da candidatura, quando associados ao parlamentar.",
    limits:
      "Resultado eleitoral e exercício atual do mandato são informações diferentes. Vínculos entre bases precisam de conferência e podem permanecer indisponíveis.",
  },
];

export default function SourcesAndPrivacyPage() {
  return (
    <div className="min-h-screen bg-[#f4f7f8]">
      <SiteHeader />
      <main id="conteudo" tabIndex={-1} className="mx-auto max-w-5xl px-5 py-12 sm:px-8 sm:py-16">
        <p className="text-sm font-semibold text-emerald-800">Transparência do portal</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[#07152d] sm:text-4xl">
          {title}
        </h1>
        <p className="mt-5 max-w-3xl text-base leading-7 text-slate-600">
          O Observa Poder organiza registros de órgãos públicos. Consulte a origem e as datas
          de cada registro para entender o que ele permite concluir. O portal não é um canal oficial
          desses órgãos e não oferece cobertura completa ou atualização em tempo real.
        </p>
        <nav
          aria-label="Nesta página"
          className="mt-7 flex flex-wrap gap-x-5 gap-y-3 text-sm font-semibold text-emerald-800"
        >
          <a className="underline underline-offset-4" href="#fontes">
            Fontes
          </a>
          <a className="underline underline-offset-4" href="#datas">
            Datas e lacunas
          </a>
          <a className="underline underline-offset-4" href="#privacidade">
            Dados pessoais
          </a>
          <a className="underline underline-offset-4" href="#correcoes">
            Correções
          </a>
        </nav>

        <section id="fontes" className="mt-12 scroll-mt-6" aria-labelledby="fontes-title">
          <h2 id="fontes-title" className="text-2xl font-semibold text-[#07152d]">
            Catálogo de fontes
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Este catálogo descreve as integrações do projeto, não certifica que todos os dados já
            tenham sido coletados. A disponibilidade deve ser conferida no registro consultado.
          </p>
          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            {sources.map((source) => (
              <article
                key={source.name}
                className="rounded-lg border border-slate-200 bg-white p-6"
              >
                <h3 className="text-lg font-semibold text-[#07152d]">
                  <a
                    href={source.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline decoration-emerald-300 underline-offset-4 hover:text-emerald-800"
                  >
                    {source.name} <span className="sr-only">(abre em nova aba)</span>↗
                  </a>
                </h3>
                <p className="mt-4 text-sm leading-6 text-slate-600">{source.coverage}</p>
                <p className="mt-4 text-sm leading-6 text-slate-700">
                  <strong>Limite de leitura:</strong> {source.limits}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section id="datas" className="mt-12 scroll-mt-6" aria-labelledby="datas-title">
          <h2 id="datas-title" className="text-2xl font-semibold text-[#07152d]">
            Datas e lacunas
          </h2>
          <dl className="mt-5 space-y-5 text-sm leading-6 text-slate-600">
            <div>
              <dt className="font-semibold text-slate-800">Data do evento ou competência</dt>
              <dd>
                Quando ocorreu a votação, despesa ou período de referência. Não é a data em que o
                portal leu o dado.
              </dd>
            </div>
            <div>
              <dt className="font-semibold text-slate-800">Data da coleta</dt>
              <dd>
                Quando o portal observou o registro na fonte. Uma nova coleta não significa que o
                órgão tenha atualizado o conteúdo. Datas de negócio seguem o horário de Brasília
                (America/Sao_Paulo).
              </dd>
            </div>
            <div>
              <dt className="font-semibold text-slate-800">Atualização na origem</dt>
              <dd>
                Depende de informação publicada pelo órgão. Quando desconhecida, não deve ser
                substituída pela data da coleta.
              </dd>
            </div>
            <div>
              <dt className="font-semibold text-slate-800">Identificadores</dt>
              <dd>
                IDs pertencem à respectiva fonte: o mesmo número em órgãos distintos não identifica
                a mesma pessoa ou matéria. Nomes iguais, isoladamente, não comprovam identidade.
              </dd>
            </div>
          </dl>
          <p className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-slate-800">
            Sem registro pode significar dado não coletado, período fora da cobertura ou informação
            não publicada. Isso não prova ausência, abstenção, gasto zero ou irregularidade. Uma
            lista de votos vazia também não comprova o tipo de votação.
          </p>
        </section>

        <section
          id="privacidade"
          className="mt-12 scroll-mt-6 space-y-4 text-sm leading-6 text-slate-600"
          aria-labelledby="privacidade-title"
        >
          <h2 id="privacidade-title" className="text-2xl font-semibold text-[#07152d]">
            Dados pessoais e documentos públicos
          </h2>
          <p>
            O foco é a atuação pública: identificação parlamentar, mandato, autoria, voto e uso de
            recursos. O importador de despesas descarta o campo CPF/CNPJ do fornecedor; esses
            documentos não fazem parte da consulta pública do portal.
          </p>
          <p>
            Nomes de servidores e fornecedores podem aparecer por sua relação com equipes e despesas
            públicas. Isso não autoriza seu uso para assédio nem permite concluir culpa ou
            irregularidade.
          </p>
          <p>
            Comprovantes e consultas oficiais podem conter dados pessoais, assinaturas ou
            informações adicionais publicadas pelo órgão. Confira se precisa abrir ou compartilhar o
            documento; evite reproduzir dados pessoais sem necessidade. O conteúdo pode mudar após a
            coleta.
          </p>
          <p>
            Os CSVs e PDFs gerados pelo portal informam o órgão publicador, o período representado e
            a data da coleta. Eles são recortes produzidos no momento do download, não documentos
            emitidos ou assinados pelo órgão. Valores ausentes permanecem como “não informado” e não
            entram em totais completos.
          </p>
          <p>
            Vínculos de remuneração e emendas baseados em nome só são publicados quando o nome
            normalizado corresponde de forma exata e única. Homônimos e aproximações ficam sem
            associação até existir evidência mais segura.
          </p>
          <p>
            As evidências internas devem ser limitadas aos campos necessários para conferir a
            origem. Os prazos de retenção e a rotina de descarte ainda precisam ser implantados e
            verificados antes da publicação do serviço.
          </p>
        </section>

        <section
          id="correcoes"
          className="mt-12 scroll-mt-6 space-y-4 text-sm leading-6 text-slate-600"
          aria-labelledby="correcoes-title"
        >
          <h2 id="correcoes-title" className="text-2xl font-semibold text-[#07152d]">
            Conferência e correções
          </h2>
          <p>
            Encontrou uma divergência? Compare o registro com a fonte oficial, observando exercício,
            competência e datas. A origem pode ter sido corrigida depois da coleta.
          </p>
          <p>
            Para documentar o problema, reúna o endereço da página do portal, o identificador do
            registro, o link oficial e uma descrição objetiva da diferença. Não inclua CPF, endereço
            residencial ou cópias integrais de documentos pessoais.
          </p>
          {hasPrivacyContact ? (
            <p>
              Envie pedidos de correção ou privacidade para{" "}
              <a className="font-semibold underline" href={`mailto:${privacyContact}`}>
                {privacyContact}
              </a>.
            </p>
          ) : (
            <p>O canal público de correções e privacidade ainda está em preparação.</p>
          )}
        </section>
        <Link
          href="/metodologia"
          className="mt-8 inline-block font-semibold text-emerald-800 underline underline-offset-4"
        >
          Como interpretar e citar os registros
        </Link>
      </main>
      <SiteFooter />
    </div>
  );
}
