"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { RecordProvenance } from "@/components/record-provenance";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

type Detail = {
  kind: string;
  number: number | null;
  year: number | null;
  summary: string;
  detailed_summary: string | null;
  presented_at: string | null;
  source_url: string;
  source: string;
  external_id: string;
  collected_at: string;
  full_text_url: string | null;
  keywords: string[];
  status_description: string | null;
  status_agency: string | null;
  status_appreciation: string | null;
  status_regime: string | null;
  status_at: string | null;
  citizen_explanation: {
    plain_summary: string;
    what_changes: string | null;
    affected_groups: string[];
    practical_example: string | null;
    impacts: string | null;
    benefits: string | null;
    cost_estimate: string | null;
    analysis: string | null;
    source_basis: string[];
    method: "editorial" | "assisted" | "automated";
    generated_at: string | null;
    generation_model: string | null;
    verification_model: string | null;
  } | null;
  related_votings: {
    id: string;
    occurred_on: string | null;
    title: string;
    approved: boolean | null;
    mode: string | null;
    relation_type: string;
  }[];
  authors: {
    parliamentarian_id: string | null;
    author_name: string;
    author_type: string | null;
    author_url: string | null;
    signature_order: number | null;
    is_proponent: boolean | null;
  }[];
  proceedings: {
    occurred_at: string | null;
    sequence: number | null;
    agency_url: string | null;
    description: string | null;
    situation: string | null;
    dispatch: string | null;
    rapporteur_url: string | null;
  }[];
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const typeDescriptions: Record<string, string> = {
  PEC: "Proposta de Emenda à Constituição",
  PL: "Projeto de Lei",
  PLP: "Projeto de Lei Complementar",
  RIC: "Requerimento de Informação",
  REQ: "Requerimento",
  RQS: "Requerimento do Senado",
  INC: "Indicação",
  PDL: "Projeto de Decreto Legislativo",
};
const examples: Record<string, string> = {
  PEC: "Uma PEC pode alterar o texto da Constituição, mas precisa cumprir um rito mais rigoroso e não depende apenas de uma votação simples.",
  PL: "Um projeto de lei propõe criar ou alterar uma regra. Ele só produz efeitos após aprovação nas Casas competentes e sanção ou promulgação.",
  PLP: "Um projeto de lei complementar trata de temas que a Constituição reservou a esse tipo de norma e exige maioria absoluta para aprovação.",
  RIC: "Um requerimento de informação solicita dados ou esclarecimentos a uma autoridade. Ele fiscaliza, mas não cria uma nova lei.",
  REQ: "Um requerimento normalmente pede uma providência dentro do processo legislativo, como audiência, urgência ou inclusão em pauta.",
  RQS: "Um requerimento organiza uma providência legislativa no Senado e não representa, por si só, uma nova obrigação para a sociedade.",
  INC: "Uma indicação sugere uma providência a outro órgão. Ela comunica uma recomendação e não tem o mesmo efeito de uma lei aprovada.",
  PDL: "Um projeto de decreto legislativo trata de competência do Congresso, como sustar atos ou decidir matérias que não dependem de sanção presidencial.",
};
const instrumentPurposes: Record<string, string> = {
  PEC: "Propõe alterar a Constituição. Para produzir efeito, precisa cumprir o rito especial previsto para emendas constitucionais.",
  PL: "Propõe criar ou alterar uma lei. A apresentação do projeto inicia o debate, mas ainda não muda as regras em vigor.",
  PLP: "Propõe criar ou alterar uma lei complementar. Esse tipo de projeto exige maioria absoluta para ser aprovado.",
  RIC: "Solicita informações ou esclarecimentos a uma autoridade. Serve à fiscalização e não cria uma nova lei.",
  REQ: "Pede uma providência dentro do processo legislativo, como uma audiência, urgência ou inclusão em pauta.",
  RQS: "Pede uma providência dentro do processo legislativo do Senado e não cria, sozinho, uma obrigação para a sociedade.",
  INC: "Sugere uma providência a outro órgão. É uma recomendação e não tem o mesmo efeito de uma lei aprovada.",
  PDL: "Trata de uma decisão de competência do Congresso que, em regra, não depende de sanção presidencial.",
};

function formatDate(value: string | null) {
  if (!value) return "Data não informada";
  return new Date(value).toLocaleDateString("pt-BR", {
    dateStyle: "long",
    timeZone: "America/Sao_Paulo",
  });
}

function propositionLabel(item: Detail) {
  return `${item.kind}${item.number ? ` ${item.number}` : ""}${item.year && item.year > 0 ? `/${item.year}` : ""}`;
}

function explainProceeding(event: Detail["proceedings"][number]) {
  const officialText = `${event.description ?? ""} ${event.situation ?? ""} ${event.dispatch ?? ""}`
    .trim()
    .toLocaleLowerCase("pt-BR");
  if (officialText.includes("arquiv"))
    return "A fonte registrou o arquivamento da matéria nesta etapa.";
  if (officialText.includes("rejeitad"))
    return "A fonte registrou uma rejeição nesta etapa do processo.";
  if (officialText.includes("aprova"))
    return "A fonte registrou uma aprovação nesta etapa. Isso não significa, sozinho, que a proposta virou lei.";
  if (officialText.includes("parecer"))
    return "Foi registrada uma manifestação ou parecer sobre a matéria; ainda pode haver outras etapas.";
  if (officialText.includes("relator"))
    return "Um parlamentar foi indicado para analisar a matéria e apresentar sua avaliação.";
  if (officialText.includes("despacho"))
    return "A Casa registrou para quais órgãos ou comissões a matéria deve seguir.";
  if (officialText.includes("apresent"))
    return "A matéria foi apresentada e passou a integrar formalmente o processo legislativo.";
  if (officialText.includes("encaminh") || officialText.includes("remet"))
    return "A matéria foi encaminhada para outra unidade ou etapa de análise.";
  if (officialText.includes("receb"))
    return "Um órgão da Casa registrou o recebimento da matéria para processamento ou análise.";
  return "A fonte oficial registrou uma atualização no andamento da matéria.";
}

function relatedVotingContext(relationType: string) {
  if (relationType === "object")
    return "A fonte identifica esta proposição como objeto da votação.";
  if (relationType === "affected")
    return "A fonte registra que esta proposição foi afetada pela decisão.";
  return "A fonte registra um vínculo com esta proposição; confira o objeto exato da votação.";
}

function votingResult(approved: boolean | null) {
  if (approved === true) return "Aprovada nesta etapa";
  if (approved === false) return "Rejeitada nesta etapa";
  return "Resultado não informado";
}

export default function PropositionPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [item, setItem] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [showAllEvents, setShowAllEvents] = useState(false);
  const events = useMemo(() => {
    if (!item) return [];
    return [...item.proceedings].sort((a, b) => {
      if (!a.occurred_at) return 1;
      if (!b.occurred_at) return -1;
      return new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime();
    });
  }, [item]);

  useEffect(() => {
    fetch(`${API}/propositions/${id}`)
      .then((response) =>
        response.ok ? response.json() : Promise.reject(new Error("Proposição não encontrada.")),
      )
      .then(setItem)
      .catch((exception) => setError(exception.message));
  }, [id]);

  const visibleEvents = showAllEvents ? events : events.slice(0, 6);
  const explanation = item?.citizen_explanation;
  const citizenSummary = explanation?.plain_summary;
  const analysisCards = item
    ? [
        ["Impactos", explanation?.impacts, "Ainda não avaliados pela plataforma."],
        ["Benefícios", explanation?.benefits, "Ainda não avaliados pela plataforma."],
        ["Custo estimado", explanation?.cost_estimate, "Nenhuma estimativa oficial identificada."],
        ["Análise", explanation?.analysis, "Os dados oficiais ainda não sustentam uma análise segura."],
      ]
    : [];

  return (
    <main className="min-h-screen bg-[var(--paper)] text-slate-950">
      <SiteHeader />
      <div className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-5 py-4 sm:px-8">
          <button
            type="button"
            onClick={() => router.back()}
            className="min-h-10 rounded-lg px-2 text-sm font-bold text-slate-600 hover:bg-slate-100 hover:text-emerald-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700"
          >
            ← Voltar aos projetos
          </button>
        </div>
      </div>
      <section id="conteudo" tabIndex={-1} className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:py-12">
        {error && <Card className="border-red-200 bg-red-50 p-6 text-red-900">{error}</Card>}
        {!item && !error && (
          <div className="space-y-5" aria-label="Carregando proposição">
            <div className="h-72 animate-pulse rounded-3xl bg-slate-200" />
            <div className="grid gap-5 lg:grid-cols-3">
              <div className="h-48 animate-pulse rounded-2xl bg-slate-200" />
              <div className="h-48 animate-pulse rounded-2xl bg-slate-200 lg:col-span-2" />
            </div>
          </div>
        )}
        {item && (
          <>
            <header className="overflow-hidden rounded-3xl bg-[#07152d] px-7 py-9 text-white shadow-xl shadow-slate-900/10 sm:px-10 sm:py-12">
              <div className="flex flex-wrap items-center gap-3">
                <Badge className="bg-emerald-300 text-emerald-950">{propositionLabel(item)}</Badge>
                <span className="text-sm font-bold text-slate-300">
                  {typeDescriptions[item.kind] ?? "Matéria legislativa"}
                </span>
              </div>
              <h1 className="mt-6 line-clamp-7 max-w-5xl text-2xl font-extrabold leading-snug tracking-tight sm:line-clamp-none sm:text-4xl sm:leading-tight lg:text-[2.65rem]">
                {item.summary || "Ementa ainda não importada"}
              </h1>
              <div className="mt-8 flex flex-wrap gap-x-8 gap-y-3 text-sm text-slate-300">
                <span>Apresentada em {formatDate(item.presented_at)}</span>
                {item.status_agency && <span>Órgão atual: {item.status_agency}</span>}
              </div>
              <RecordProvenance
                source={item.source}
                externalId={item.external_id}
                collectedAt={item.collected_at}
              />
              <div className="mt-7 flex flex-wrap gap-3">
                {item.full_text_url && (
                  <a
                    href={item.full_text_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex min-h-11 items-center rounded-xl bg-emerald-300 px-5 text-sm font-extrabold text-emerald-950 hover:bg-emerald-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
                  >
                    Ler texto integral ↗
                  </a>
                )}
                <a
                  href={item.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex min-h-11 items-center rounded-xl border border-white/25 px-5 text-sm font-bold text-white hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
                >
                  Ver registro oficial ↗
                </a>
              </div>
            </header>

            <section className="mt-6 overflow-hidden rounded-3xl border border-emerald-200 bg-white shadow-sm">
              <div className="border-b border-emerald-100 bg-emerald-50 px-6 py-6 sm:px-8">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-extrabold uppercase tracking-widest text-emerald-800">
                      Leitura cidadã
                    </p>
                    <h2 className="mt-2 text-3xl font-extrabold text-slate-950">
                      Entenda em 1 minuto
                    </h2>
                  </div>
                  <span
                    className={`rounded-full px-3 py-1.5 text-xs font-extrabold ${explanation ? "bg-emerald-700 text-white" : "bg-amber-100 text-amber-900"}`}
                  >
                    {explanation ? "Gerada e verificada automaticamente" : "Em preparação"}
                  </span>
                </div>
                {!explanation && (
                  <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-600">
                    A automação ainda não publicou uma explicação para esta matéria. Isso ocorre
                    quando os dados são insuficientes ou alguma validação não foi superada. A ementa
                    oficial continua disponível no topo.
                  </p>
                )}
              </div>

              <div className="grid gap-px bg-slate-200 lg:grid-cols-2">
                <article className="bg-white p-6 sm:p-8 lg:col-span-2">
                  <p className="text-sm font-extrabold text-emerald-800">Em poucas palavras</p>
                  {citizenSummary ? (
                    <p className="mt-3 max-w-5xl text-xl font-bold leading-8 text-slate-950">
                      {citizenSummary}
                    </p>
                  ) : (
                    <div className="mt-3 max-w-3xl rounded-2xl border border-dashed border-amber-300 bg-amber-50 p-5">
                      <p className="font-extrabold text-amber-950">
                        Explicação automática sendo preparada
                      </p>
                      <p className="mt-2 leading-7 text-amber-900">
                        O sistema tentará novamente após consultar os dados oficiais. Nenhum texto é
                        publicado sem passar pelas validações automáticas de fidelidade e clareza.
                      </p>
                    </div>
                  )}
                </article>
                <article className="bg-white p-6 sm:p-8">
                  <p className="text-sm font-extrabold text-slate-950">O que pretende fazer</p>
                  <p className="mt-3 leading-7 text-slate-600">
                    {explanation?.what_changes ||
                      instrumentPurposes[item.kind] ||
                      "A sigla identifica um instrumento do processo legislativo. O efeito concreto depende do texto e das etapas de tramitação."}
                  </p>
                </article>
                <article className="bg-white p-6 sm:p-8">
                  <p className="text-sm font-extrabold text-slate-950">Quem pode ser afetado</p>
                  {explanation?.affected_groups.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {explanation.affected_groups.map((group) => (
                        <Badge key={group}>{group}</Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-3 leading-7 text-slate-600">
                      Os dados oficiais ainda não sustentam uma identificação segura do público.
                    </p>
                  )}
                </article>
                <article className="bg-white p-6 sm:p-8">
                  <p className="text-sm font-extrabold text-slate-950">Exemplo prático</p>
                  <p className="mt-3 leading-7 text-slate-600">
                    {explanation?.practical_example ||
                      examples[item.kind] ||
                      "O efeito prático depende do tipo da matéria, do texto aprovado e das etapas seguintes."}
                  </p>
                  {!explanation?.practical_example && (
                    <p className="mt-3 text-xs font-semibold text-slate-500">
                      Exemplo educativo sobre o tipo da matéria, não sobre o resultado deste
                      projeto.
                    </p>
                  )}
                </article>
                <article className="bg-white p-6 sm:p-8">
                  <p className="text-sm font-extrabold text-slate-950">Em que ponto está</p>
                  <p className="mt-3 leading-7 text-slate-600">
                    {item.status_description
                      ? `A situação oficial mais recente é: ${item.status_description}${item.status_agency ? `, no órgão ${item.status_agency}` : ""}.`
                      : "A fonte ainda não forneceu uma situação estruturada para esta matéria."}
                  </p>
                  <p className="mt-3 text-xs font-semibold text-slate-500">
                    A plataforma não presume qual será a próxima etapa.
                  </p>
                </article>
              </div>

              {explanation?.source_basis.length ? (
                <div className="border-t border-slate-200 bg-slate-50 px-6 py-4 sm:px-8">
                  <p className="text-xs font-bold text-slate-500">
                    Conteúdo gerado por IA e verificado automaticamente com base em {explanation.source_basis.length} fonte(s) oficial(is)
                    {explanation.generated_at
                      ? ` · publicado em ${formatDate(explanation.generated_at)}`
                      : ""}
                  </p>
                </div>
              ) : null}
            </section>

            {(item.status_description || item.status_appreciation || item.status_regime) && (
              <Card className="mt-6 border-emerald-200 bg-emerald-50 p-6">
                <p className="text-xs font-extrabold uppercase tracking-widest text-emerald-800">
                  Situação oficial mais recente
                </p>
                <p className="mt-3 text-lg font-bold text-slate-950">
                  {item.status_description || "Situação sem descrição"}
                </p>
                <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
                  {item.status_at && <span>Atualizada em {formatDate(item.status_at)}</span>}
                  {item.status_appreciation && <span>Apreciação: {item.status_appreciation}</span>}
                  {item.status_regime && item.status_regime !== "." && (
                    <span>Regime: {item.status_regime}</span>
                  )}
                </div>
              </Card>
            )}

            <details className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm open:ring-2 open:ring-emerald-100 sm:p-7">
              <summary className="cursor-pointer list-none font-extrabold text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700">
                Consultar a ementa oficial e os termos da fonte
              </summary>
              <p className="mt-5 text-lg leading-8 text-slate-700">
                {item.detailed_summary || item.summary || "Ementa oficial ainda não importada."}
              </p>
              <p className="mt-5 border-t border-slate-100 pt-4 text-sm leading-6 text-slate-500">
                A ementa é publicada pela Casa legislativa. Para conferir artigos, exceções e regras
                de transição, consulte o texto integral.
              </p>
              {item.keywords.length > 0 && (
                <div className="mt-5 flex flex-wrap gap-2">
                  {item.keywords.map((keyword) => (
                    <Badge key={keyword}>{keyword}</Badge>
                  ))}
                </div>
              )}
            </details>

            <section className="mt-6">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-xs font-extrabold uppercase tracking-widest text-emerald-700">
                    Leitura responsável
                  </p>
                  <h2 className="mt-2 text-2xl font-extrabold">Impacto e análise</h2>
                </div>
                <p className="max-w-xl text-sm leading-6 text-slate-500">
                  Estes campos só recebem conteúdo após avaliação documentada. Ausência de análise
                  não significa ausência de impacto.
                </p>
              </div>
              <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {analysisCards.map(([title, content, fallback]) => (
                  <Card key={title} className="p-5">
                    <p className="font-extrabold text-slate-950">{title}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{content || fallback}</p>
                    <span
                      className={`mt-4 inline-block rounded-full px-3 py-1 text-xs font-bold ${content ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}
                    >
                      {content ? "Conteúdo revisado" : "Pendente de avaliação"}
                    </span>
                  </Card>
                ))}
              </div>
            </section>

            <section className="mt-6 rounded-3xl bg-[#07152d] p-6 text-white shadow-sm sm:p-8">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="text-xs font-extrabold uppercase tracking-widest text-emerald-300">
                    Projeto e decisões
                  </p>
                  <h2 className="mt-2 text-2xl font-extrabold sm:text-3xl">
                    Este projeto já apareceu em votações?
                  </h2>
                </div>
                <span className="rounded-full bg-white/10 px-3 py-1.5 text-xs font-bold text-slate-200">
                  {item.related_votings.length}{" "}
                  {item.related_votings.length === 1 ? "registro" : "registros"}
                </span>
              </div>
              <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-300">
                Uma votação relacionada pode tratar do projeto inteiro, de uma emenda, de um parecer
                ou de um requerimento. Aprovação em uma etapa não significa que a matéria virou lei.
              </p>

              {item.related_votings.length > 0 ? (
                <div className="mt-6 grid gap-4 lg:grid-cols-2">
                  {item.related_votings.map((voting) => (
                    <Link
                      key={voting.id}
                      href={`/votacoes/${voting.id}`}
                      className="group rounded-2xl border border-white/15 bg-white/5 p-5 transition hover:border-emerald-300 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300"
                    >
                      <div className="flex flex-wrap items-center gap-2 text-xs font-bold">
                        <span className="rounded-full bg-emerald-300 px-3 py-1 text-emerald-950">
                          {votingResult(voting.approved)}
                        </span>
                        <span className="text-slate-400">{formatDate(voting.occurred_on)}</span>
                        <span className="text-slate-400">
                          {voting.mode === "nominal"
                            ? "Votação nominal"
                            : "Modalidade não informada"}
                        </span>
                      </div>
                      <h3 className="mt-4 line-clamp-3 text-lg font-extrabold leading-7">
                        {voting.title}
                      </h3>
                      <p className="mt-3 text-sm leading-6 text-slate-300">
                        {relatedVotingContext(voting.relation_type)}
                      </p>
                      <p className="mt-4 text-sm font-bold text-emerald-300">
                        Entender esta votação <span aria-hidden="true">→</span>
                      </p>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="mt-6 rounded-2xl border border-dashed border-white/20 bg-white/5 p-5">
                  <p className="font-bold">Nenhuma votação relacionada foi importada.</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    Isso não prova que a matéria nunca foi votada; significa apenas que a base local
                    ainda não possui um vínculo oficial para exibir.
                  </p>
                </div>
              )}
            </section>

            <div className="mt-6 grid gap-6 lg:grid-cols-[0.75fr_1.25fr]">
              <Card className="p-7 shadow-sm">
                <div className="flex items-end justify-between gap-4">
                  <div>
                    <p className="text-xs font-extrabold uppercase tracking-widest text-emerald-700">
                      Autoria oficial
                    </p>
                    <h2 className="mt-2 text-2xl font-extrabold">Autores</h2>
                  </div>
                  <span className="text-sm text-slate-500">{item.authors.length}</span>
                </div>
                <div className="mt-6 space-y-3">
                  {item.authors.map((author, index) => {
                    const content = (
                      <>
                        <p className="font-bold text-slate-950">{author.author_name}</p>
                        <p className="mt-1 text-sm text-slate-500">
                          {author.author_type ?? "Autor da proposição"}
                          {author.is_proponent === true ? " · Proponente" : ""}
                        </p>
                      </>
                    );
                    return author.parliamentarian_id ? (
                      <Link
                        key={`${author.author_name}-${index}`}
                        href={`/parlamentares/${author.parliamentarian_id}`}
                        className="block rounded-xl bg-slate-50 px-4 py-3 hover:bg-emerald-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700"
                      >
                        {content}
                      </Link>
                    ) : (
                      <div
                        key={`${author.author_name}-${index}`}
                        className="rounded-xl bg-slate-50 px-4 py-3"
                      >
                        {content}
                      </div>
                    );
                  })}
                  {item.authors.length === 0 && (
                    <p className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                      A autoria ainda não foi importada. O coletor fará novas tentativas com a fonte
                      oficial.
                    </p>
                  )}
                </div>
              </Card>

              <Card className="p-7 shadow-sm">
                <div className="flex items-end justify-between gap-4">
                  <div>
                    <p className="text-xs font-extrabold uppercase tracking-widest text-emerald-700">
                      Histórico explicado
                    </p>
                    <h2 className="mt-2 text-2xl font-extrabold">O caminho da proposta</h2>
                  </div>
                  <span className="text-sm text-slate-500">{events.length} eventos</span>
                </div>
                {visibleEvents.length > 0 ? (
                  <ol className="mt-7 space-y-6 border-l border-emerald-200 pl-6">
                    {visibleEvents.map((event, index) => (
                      <li key={`${event.sequence}-${index}`} className="relative">
                        <span className="absolute -left-[31px] top-1.5 h-2.5 w-2.5 rounded-full bg-emerald-600 ring-4 ring-white" />
                        <p className="font-bold leading-6 text-slate-950">
                          {explainProceeding(event)}
                        </p>
                        <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                          {formatDate(event.occurred_at)}
                        </p>
                        <details className="mt-3 text-sm text-slate-600">
                          <summary className="cursor-pointer font-bold text-emerald-800">
                            Ver registro oficial desta etapa
                          </summary>
                          <p className="mt-2 leading-6">
                            {event.description || event.situation || "Atualização legislativa"}
                          </p>
                          {event.dispatch && <p className="mt-2 leading-6">{event.dispatch}</p>}
                        </details>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-6 rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                    Nenhum evento de tramitação foi importado.
                  </p>
                )}
                {events.length > 6 && (
                  <button
                    type="button"
                    onClick={() => setShowAllEvents((current) => !current)}
                    className="mt-6 min-h-11 rounded-xl border border-slate-300 px-4 text-sm font-bold text-slate-800 hover:border-emerald-600 hover:text-emerald-800"
                  >
                    {showAllEvents ? "Mostrar menos" : `Ver todos os ${events.length} eventos`}
                  </button>
                )}
              </Card>
            </div>
          </>
        )}
      </section>
      <SiteFooter />
    </main>
  );
}
