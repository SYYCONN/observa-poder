"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { RecordProvenance } from "@/components/record-provenance";
import { SiteFooter, SiteHeader } from "@/components/site-header";
type Detail = {
  occurred_on: string | null;
  description: string;
  object_description: string | null;
  approved: boolean | null;
  mode: string | null;
  source_url: string;
  source: string;
  external_id: string;
  collected_at: string;
  propositions: { proposition_id: string; relation_type: string; proposition_label: string }[];
  votes: {
    parliamentarian_id: string;
    parliamentarian_name: string;
    position: string;
    party_at_vote: string | null;
    state_at_vote: string | null;
  }[];
};
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const relationLabels: Record<string, string> = {
  object: "Objeto da votação",
  possible_object: "Objeto relacionado",
  affected: "Proposição afetada",
};

function voteGroup(position: string) {
  const normalized = position.trim().toLowerCase();
  if (normalized === "sim") return "sim";
  if (normalized === "não" || normalized === "nao") return "nao";
  return "outros";
}

export default function VotingPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [item, setItem] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<"todos" | "sim" | "nao" | "outros">("todos");
  const [voteSearch, setVoteSearch] = useState("");
  const voteSummary = useMemo(() => {
    const totals = { yes: 0, no: 0, other: 0 };
    const parties = new Map<string, { yes: number; no: number; other: number }>();
    for (const vote of item?.votes ?? []) {
      const key = vote.party_at_vote ?? "Partido não informado";
      const party = parties.get(key) ?? { yes: 0, no: 0, other: 0 };
      const position = voteGroup(vote.position);
      if (position === "sim") {
        totals.yes += 1;
        party.yes += 1;
      } else if (position === "nao") {
        totals.no += 1;
        party.no += 1;
      } else {
        totals.other += 1;
        party.other += 1;
      }
      parties.set(key, party);
    }
    return { ...totals, parties: [...parties.entries()] };
  }, [item]);
  const partyChart = voteSummary.parties.map(([party, values]) => ({
    party,
    Sim: values.yes,
    Não: values.no,
    Outros: values.other,
  }));
  const visibleVotes = item?.votes.filter((vote) => {
    const matchesPosition = filter === "todos" || voteGroup(vote.position) === filter;
    const term = voteSearch.trim().toLocaleLowerCase("pt-BR");
    const matchesSearch =
      !term ||
      vote.parliamentarian_name.toLocaleLowerCase("pt-BR").includes(term) ||
      (vote.party_at_vote ?? "").toLocaleLowerCase("pt-BR").includes(term) ||
      (vote.state_at_vote ?? "").toLocaleLowerCase("pt-BR").includes(term);
    return matchesPosition && matchesSearch;
  });
  useEffect(() => {
    fetch(`${API}/votings/${id}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("Votação não encontrada."))))
      .then(setItem)
      .catch((e) => setError(e.message));
  }, [id]);
  return (
    <main className="min-h-screen bg-[var(--paper)]">
      <SiteHeader />
      <section
        id="conteudo"
        tabIndex={-1}
        className="mx-auto max-w-6xl px-5 py-10 sm:px-8 lg:py-14"
      >
        <button
          type="button"
          onClick={() => router.back()}
          className="text-sm font-semibold text-slate-600 hover:text-emerald-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700"
        >
          ← Voltar para votações
        </button>
        {error && <div className="rounded-xl bg-red-50 p-5 text-red-800">{error}</div>}
        {!item && !error && <p className="text-slate-500">Carregando votação…</p>}
        {item && (
          <>
            <header className="mt-6 rounded-[2rem] bg-[#07152d] p-7 text-white shadow-xl shadow-slate-900/10 sm:p-10">
              <p className="text-sm font-bold tracking-[0.16em] text-emerald-300">
                Votação · {item.occurred_on ?? "data não informada"}
              </p>
              <h1 className="mt-4 max-w-4xl text-2xl font-bold leading-snug tracking-tight sm:text-5xl sm:leading-tight">
                {item.object_description || item.description}
              </h1>
              <p className="mt-5 text-slate-300">
                Resultado registrado:{" "}
                {item.approved === true
                  ? "aprovada"
                  : item.approved === false
                    ? "rejeitada"
                    : "não informado"}
              </p>
              <div className="mt-6 inline-flex rounded-full bg-white/10 px-4 py-2 text-sm font-bold text-slate-100">
                {item.mode === "nominal"
                  ? "Modalidade: votação nominal"
                  : "Modalidade não identificada"}
              </div>
              <RecordProvenance
                source={item.source}
                externalId={item.external_id}
                collectedAt={item.collected_at}
              />
              <a
                href={item.source_url}
                target="_blank"
                rel="noreferrer"
                className="mt-6 inline-block font-semibold text-emerald-300 hover:underline"
              >
                Consultar fonte oficial ↗
              </a>
            </header>
            <section className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
                <p className="text-sm font-extrabold uppercase tracking-widest text-emerald-800">
                  Como foi votado
                </p>
                <h2 className="mt-2 text-xl font-extrabold text-slate-950">
                  {item.mode === "nominal" ? "Votação nominal" : "Modalidade não identificada"}
                </h2>
                <p className="mt-3 leading-7 text-slate-700">
                  {item.mode === "nominal"
                    ? "Na votação nominal, a fonte registra a posição individual de cada parlamentar. A lista abaixo contém somente os votos efetivamente publicados e importados."
                    : "A fonte importada não identificou esta votação como nominal. Sem essa informação, a plataforma não presume como cada parlamentar votou."}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-6">
                <p className="text-sm font-extrabold uppercase tracking-widest text-slate-500">
                  O que o resultado significa
                </p>
                <p className="mt-3 leading-7 text-slate-700">
                  O resultado se refere ao objeto descrito pela Casa legislativa nesta etapa. Uma
                  matéria pode passar por outras votações, redação final ou análise em outra Casa.
                </p>
              </div>
            </section>
            <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-bold tracking-[0.16em] text-emerald-700">
                Proposições relacionadas
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                {item.propositions.map((prop) => (
                  <Link
                    key={`${prop.proposition_id}-${prop.relation_type}`}
                    href={`/proposicoes/${prop.proposition_id}`}
                    className="rounded-full bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-800"
                  >
                    {prop.proposition_label} · {relationLabels[prop.relation_type] ?? "Relacionada"}
                  </Link>
                ))}
                {item.propositions.length === 0 && (
                  <p className="text-sm text-slate-500">
                    Nenhuma proposição relacionada importada.
                  </p>
                )}
              </div>
            </section>
            <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-end justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-widest text-emerald-700">
                    Registro nominal
                  </p>
                  <h2 className="mt-2 text-2xl font-bold">Votos publicados</h2>
                </div>
                <p className="text-sm text-slate-500">
                  {item.votes.length} {item.votes.length === 1 ? "registro" : "registros"}
                </p>
              </div>
              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl bg-emerald-50 p-4">
                  <p className="text-sm text-emerald-800">Sim</p>
                  <p className="mt-1 text-3xl font-extrabold text-emerald-900">{voteSummary.yes}</p>
                </div>
                <div className="rounded-xl bg-red-50 p-4">
                  <p className="text-sm text-red-800">Não</p>
                  <p className="mt-1 text-3xl font-extrabold text-red-900">{voteSummary.no}</p>
                </div>
                <div className="rounded-xl bg-slate-100 p-4">
                  <p className="text-sm text-slate-600">Outros</p>
                  <p className="mt-1 text-3xl font-extrabold text-slate-900">{voteSummary.other}</p>
                </div>
              </div>
              {partyChart.length > 0 && (
                <div className="mt-8 border-t border-slate-100 pt-7">
                  <div className="mb-4">
                    <h3 className="text-lg font-bold text-slate-950">Distribuição por partido</h3>
                    <p className="mt-1 text-sm text-slate-500">
                      Totais entre os votos nominais publicados para esta votação.
                    </p>
                  </div>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={partyChart}
                        margin={{ top: 8, right: 8, left: -20, bottom: 0 }}
                      >
                        <CartesianGrid stroke="#e2e8f0" vertical={false} />
                        <XAxis
                          dataKey="party"
                          tick={{ fontSize: 11 }}
                          tickLine={false}
                          axisLine={false}
                        />
                        <YAxis
                          allowDecimals={false}
                          tick={{ fontSize: 11 }}
                          tickLine={false}
                          axisLine={false}
                        />
                        <Tooltip cursor={{ fill: "#f1f5f9" }} />
                        <Bar dataKey="Sim" stackId="votes" fill="#087f63" radius={[3, 3, 0, 0]} />
                        <Bar dataKey="Não" stackId="votes" fill="#c45a5a" />
                        <Bar dataKey="Outros" stackId="votes" fill="#94a3b8" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
              <div className="mt-7 grid gap-4 border-t border-slate-100 pt-6 sm:grid-cols-[1fr_auto] sm:items-end">
                <label>
                  <span className="mb-2 block text-sm font-bold text-slate-800">
                    Buscar parlamentar, partido ou UF
                  </span>
                  <input
                    type="search"
                    value={voteSearch}
                    onChange={(event) => setVoteSearch(event.target.value)}
                    placeholder="Ex.: Maria, PT ou SP"
                    className="min-h-11 w-full rounded-xl border border-slate-300 px-4 text-sm outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                  />
                </label>
                <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar votos">
                  {(
                    [
                      ["todos", "Todos"],
                      ["sim", "Sim"],
                      ["nao", "Não"],
                      ["outros", "Outros"],
                    ] as const
                  ).map(([option, label]) => (
                    <button
                      key={option}
                      onClick={() => setFilter(option)}
                      className={`rounded-full px-4 py-2 text-sm font-semibold ${filter === option ? "bg-slate-950 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-8 overflow-x-auto">
                <h3 className="mb-3 text-lg font-bold">Totais por partido</h3>
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b text-slate-500">
                      <th className="px-3 py-2">Partido</th>
                      <th className="px-3 py-2">Sim</th>
                      <th className="px-3 py-2">Não</th>
                      <th className="px-3 py-2">Outros</th>
                    </tr>
                  </thead>
                  <tbody>
                    {voteSummary.parties.map(([party, values]) => (
                      <tr key={party} className="border-b last:border-0">
                        <td className="px-3 py-2 font-semibold">{party}</td>
                        <td className="px-3 py-2 text-emerald-700">{values.yes}</td>
                        <td className="px-3 py-2 text-red-700">{values.no}</td>
                        <td className="px-3 py-2 text-slate-500">{values.other}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {item.votes.length === 0 ? (
                <p className="mt-5 text-sm text-slate-500">
                  Nenhum voto individual foi importado para esta votação. Consulte a fonte oficial
                  para verificar os registros disponíveis.
                </p>
              ) : (
                <div className="mt-5 overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b text-slate-500">
                        <th className="px-3 py-3">Parlamentar</th>
                        <th className="px-3 py-3">Voto</th>
                        <th className="px-3 py-3">UF</th>
                        <th className="px-3 py-3">Partido</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleVotes?.map((vote) => (
                        <tr key={vote.parliamentarian_id} className="border-b last:border-0">
                          <td className="px-3 py-3 font-semibold">
                            <Link
                              href={`/parlamentares/${vote.parliamentarian_id}`}
                              className="text-slate-950 hover:text-emerald-800 hover:underline"
                            >
                              {vote.parliamentarian_name}
                            </Link>
                          </td>
                          <td className="px-3 py-3">{vote.position}</td>
                          <td className="px-3 py-3">{vote.state_at_vote ?? "—"}</td>
                          <td className="px-3 py-3">{vote.party_at_vote ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {visibleVotes?.length === 0 && (
                    <p className="py-8 text-center text-sm text-slate-500">
                      Nenhum voto corresponde aos filtros informados.
                    </p>
                  )}
                </div>
              )}
            </section>
          </>
        )}
      </section>
      <SiteFooter />
    </main>
  );
}
