"use client";

import Link from "next/link";
import { FormEvent, type ReactNode, useEffect, useState } from "react";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import {
  fetchParliamentarians,
  Parliamentarian,
  Proposition,
  searchPropositions,
  searchVotings,
  Voting,
} from "@/lib/api";

type SearchResults = {
  parliamentarians: Parliamentarian[];
  propositions: Proposition[];
  votings: Voting[];
};

const emptyResults: SearchResults = {
  parliamentarians: [],
  propositions: [],
  votings: [],
};

function readQuery() {
  if (typeof window === "undefined") return "";
  return new URLSearchParams(window.location.search).get("q")?.trim() ?? "";
}

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function sourceLabel(source: "camara" | "senado") {
  return source === "camara" ? "Câmara dos Deputados" : "Senado Federal";
}

function propositionLabel(item: Proposition) {
  const number = item.number ? ` ${item.number}` : "";
  const year = item.year ? `/${item.year}` : "";
  return `${item.kind}${number}${year}`;
}

function formatDate(value: string | null) {
  if (!value) return "Data não informada";
  return new Date(value).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "America/Sao_Paulo",
  });
}

export function SearchPageContent() {
  const [draftQuery, setDraftQuery] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResults>(emptyResults);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const initialQuery = readQuery();
    setDraftQuery(initialQuery);
    setQuery(initialQuery);
  }, []);

  useEffect(() => {
    if (!query) {
      setResults(emptyResults);
      setLoading(false);
      setError("");
      return;
    }

    let active = true;
    setLoading(true);
    setError("");

    void Promise.all([
      fetchParliamentarians({
        search: query,
        source: "camara",
        status: "all",
        limit: 5,
      }),
      fetchParliamentarians({
        search: query,
        source: "senado",
        status: "all",
        limit: 5,
      }),
      searchPropositions({ source: "camara", q: query, limit: 5 }),
      searchPropositions({ source: "senado", q: query, limit: 5 }),
      searchVotings({ source: "camara", q: query, limit: 5 }),
      searchVotings({ source: "senado", q: query, limit: 5 }),
    ])
      .then(
        ([
          camaraPeople,
          senadoPeople,
          camaraProjects,
          senadoProjects,
          camaraVotes,
          senadoVotes,
        ]) => {
          if (!active) return;
          setResults({
            parliamentarians: [...camaraPeople.items, ...senadoPeople.items],
            propositions: [...camaraProjects.items, ...senadoProjects.items],
            votings: [...camaraVotes.items, ...senadoVotes.items],
          });
        },
      )
      .catch((exception) => {
        if (active) {
          setError(
            exception instanceof Error
              ? exception.message
              : "Não foi possível realizar a pesquisa agora.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [query]);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextQuery = draftQuery.trim();
    const destination = nextQuery ? `/pesquisa?q=${encodeURIComponent(nextQuery)}` : "/pesquisa";
    window.history.pushState({}, "", destination);
    setQuery(nextQuery);
  }

  const total =
    results.parliamentarians.length + results.propositions.length + results.votings.length;

  return (
    <div className="min-h-screen bg-[var(--paper)]">
      <SiteHeader />
      <main id="conteudo" tabIndex={-1}>
        <section className="bg-[#07152d] text-white">
          <div className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-18">
            <p className="text-sm font-bold uppercase tracking-[0.16em] text-emerald-300">
              Pesquisa central
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
              Encontre informações públicas em um só lugar
            </h1>
            <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-300">
              Pesquise parlamentares, projetos e votações. Cada resultado leva à ficha do portal e
              mantém o link para a fonte oficial.
            </p>
            <form
              onSubmit={submitSearch}
              className="mt-8 flex max-w-3xl flex-col gap-3 sm:flex-row"
              role="search"
            >
              <label className="sr-only" htmlFor="portal-search">
                Pesquisar no portal
              </label>
              <input
                id="portal-search"
                type="search"
                value={draftQuery}
                onChange={(event) => setDraftQuery(event.target.value)}
                placeholder="Nome, partido, projeto ou votação"
                className="min-h-12 flex-1 rounded border border-white/20 bg-white px-4 text-base text-[#07152d] outline-none placeholder:text-slate-400 focus:border-emerald-300 focus:ring-2 focus:ring-emerald-200"
              />
              <button
                type="submit"
                className="min-h-12 rounded bg-emerald-500 px-6 text-sm font-bold text-[#062c26] transition hover:bg-emerald-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200"
              >
                Pesquisar
              </button>
            </form>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-12">
          {!query && (
            <div className="border-y border-slate-200 bg-white px-5 py-14 text-center sm:px-8">
              <p className="text-lg font-semibold text-[#07152d]">Comece uma pesquisa</p>
              <p className="mt-2 text-sm text-slate-600">
                Digite um nome, partido, projeto ou votação para consultar os registros disponíveis.
              </p>
            </div>
          )}

          {query && (
            <>
              <div className="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 pb-5">
                <div>
                  <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">
                    Resultados para
                  </p>
                  <h2 className="mt-2 text-3xl font-bold text-slate-950">“{query}”</h2>
                </div>
                <p className="text-sm text-slate-500" aria-live="polite">
                  {loading ? "Pesquisando…" : `${total} resultado${total === 1 ? "" : "s"}`}
                </p>
              </div>

              {error && (
                <div
                  className="mt-6 border border-red-200 bg-red-50 p-4 text-sm text-red-800"
                  role="alert"
                >
                  {error}
                </div>
              )}

              {!loading && !error && total === 0 && (
                <div className="mt-6 border border-slate-200 bg-white px-5 py-14 text-center sm:px-8">
                  <p className="font-semibold text-[#07152d]">Nenhum resultado encontrado.</p>
                  <p className="mt-2 text-sm text-slate-600">
                    Tente buscar por outro nome, número, partido ou palavra-chave.
                  </p>
                </div>
              )}

              {results.parliamentarians.length > 0 && (
                <ResultSection title="Parlamentares" count={results.parliamentarians.length}>
                  {results.parliamentarians.map((person) => (
                    <Link
                      key={`${person.source}-${person.id}`}
                      href={`/parlamentares/${person.id}`}
                      className="group flex items-center gap-4 border-b border-slate-200 bg-white px-5 py-4 transition hover:bg-emerald-50/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-700 sm:px-6"
                    >
                      <span className="grid size-12 shrink-0 place-items-center rounded-full bg-emerald-50 text-sm font-bold text-emerald-800">
                        {initials(person.name)}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-semibold text-[#07152d] group-hover:text-emerald-800">
                          {person.name}
                        </span>
                        <span className="mt-1 block text-sm text-slate-500">
                          {sourceLabel(person.source)} · {person.party ?? "Partido não informado"}
                          {person.state ? ` · ${person.state}` : ""}
                        </span>
                      </span>
                      <span className="text-sm font-bold text-emerald-800">Ver perfil →</span>
                    </Link>
                  ))}
                </ResultSection>
              )}

              {results.propositions.length > 0 && (
                <ResultSection title="Projetos e proposições" count={results.propositions.length}>
                  {results.propositions.map((item) => (
                    <Link
                      key={`${item.source}-${item.id}`}
                      href={`/proposicoes/${item.id}`}
                      className="group block border-b border-slate-200 bg-white px-5 py-4 transition hover:bg-emerald-50/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-700 sm:px-6"
                    >
                      <span className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-sm font-bold text-emerald-800">
                          {propositionLabel(item)}
                        </span>
                        <span className="text-xs text-slate-500">{sourceLabel(item.source)}</span>
                      </span>
                      <span className="mt-2 block line-clamp-2 font-semibold leading-6 text-[#07152d] group-hover:text-emerald-800">
                        {item.summary || "Ementa ainda não importada"}
                      </span>
                    </Link>
                  ))}
                </ResultSection>
              )}

              {results.votings.length > 0 && (
                <ResultSection title="Votações" count={results.votings.length}>
                  {results.votings.map((item) => (
                    <Link
                      key={`${item.source}-${item.id}`}
                      href={`/votacoes/${item.id}`}
                      className="group block border-b border-slate-200 bg-white px-5 py-4 transition hover:bg-emerald-50/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-700 sm:px-6"
                    >
                      <span className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-sm font-bold text-emerald-800">
                          {formatDate(item.occurred_on)}
                        </span>
                        <span className="text-xs text-slate-500">{sourceLabel(item.source)}</span>
                      </span>
                      <span className="mt-2 block line-clamp-2 font-semibold leading-6 text-[#07152d] group-hover:text-emerald-800">
                        {item.description || item.object_description || "Votação sem descrição"}
                      </span>
                    </Link>
                  ))}
                </ResultSection>
              )}
            </>
          )}
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

function ResultSection({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: ReactNode;
}) {
  return (
    <section className="mt-10">
      <div className="mb-3 flex items-center justify-between gap-4">
        <h3 className="text-xl font-bold text-[#07152d]">{title}</h3>
        <span className="text-sm text-slate-500">
          {count} encontrado{count === 1 ? "" : "s"}
        </span>
      </div>
      <div className="overflow-hidden border-y border-slate-200">{children}</div>
    </section>
  );
}
