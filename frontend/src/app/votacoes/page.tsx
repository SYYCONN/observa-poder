"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { FilterSelect } from "@/components/filter-select";
import { LegislationPagination } from "@/components/legislation-pagination";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Voting, VotingPage, searchVotings } from "@/lib/api";

const PAGE_SIZE = 12;

function resultLabel(item: Voting) {
  if (item.approved === true)
    return { label: "Aprovada", style: "bg-emerald-100 text-emerald-900" };
  if (item.approved === false) return { label: "Rejeitada", style: "bg-red-100 text-red-900" };
  return { label: "Resultado não informado", style: "bg-slate-100 text-slate-700" };
}

function modeLabel(mode: string | null) {
  return mode === "nominal" ? "Votação nominal" : "Modalidade não identificada";
}

function votingTitle(item: Voting) {
  return item.object_description?.trim() || item.description?.trim() || "Votação sem descrição";
}

function recordsLabel(total: number) {
  return `${total.toLocaleString("pt-BR")} ${total === 1 ? "registro" : "registros"}`;
}

function formatDate(value: string | null) {
  if (!value) return "Data não informada";
  return new Date(`${value}T12:00:00`).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function VotacoesPage() {
  const [source, setSource] = useState<"camara" | "senado">("camara");
  const [draftSearch, setDraftSearch] = useState("");
  const [search, setSearch] = useState("");
  const [year, setYear] = useState("");
  const [result, setResult] = useState<"approved" | "rejected" | "unknown" | "">("");
  const [mode, setMode] = useState<"nominal" | "unknown" | "">("");
  const [order, setOrder] = useState<"newest" | "oldest">("newest");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<VotingPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void searchVotings({
      source,
      q: search,
      year,
      result,
      mode,
      order,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    })
      .then((response) => {
        if (active) setData(response);
      })
      .catch((exception) => {
        if (active) {
          setError(
            exception instanceof Error ? exception.message : "Não foi possível carregar votações.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [source, search, year, result, mode, order, page]);

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setSearch(draftSearch.trim());
    setPage(1);
  }

  function resetFilters() {
    setDraftSearch("");
    setSearch("");
    setYear("");
    setResult("");
    setMode("");
    setOrder("newest");
    setPage(1);
  }

  function changeSource(nextSource: "camara" | "senado") {
    setSource(nextSource);
    setYear("");
    setResult("");
    setMode("");
    setPage(1);
  }

  const hasFilters = Boolean(search || year || result || mode || order !== "newest");

  return (
    <main className="min-h-screen bg-[var(--paper)]">
      <SiteHeader />
      <section id="conteudo" tabIndex={-1} className="bg-[#07152d] text-white">
        <div className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-18">
          <div className="grid items-end gap-8 lg:grid-cols-[1fr_auto]">
            <div>
              <p className="text-sm font-bold tracking-[0.16em] text-emerald-300">
                Decisões legislativas
              </p>
              <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl">Votações</h1>
              <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-300">
                Encontre uma decisão, entenda sua modalidade e consulte os votos individuais quando
                a fonte publicou uma votação nominal.
              </p>
            </div>
            <div className="rounded-2xl border border-white/15 bg-white/5 px-5 py-4 backdrop-blur">
              <p className="text-xs font-bold uppercase tracking-widest text-slate-400">
                Registros encontrados
              </p>
              <p className="mt-1 text-3xl font-extrabold" aria-live="polite">
                {loading && !data ? "—" : (data?.total ?? 0).toLocaleString("pt-BR")}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-12">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">
              Casa legislativa
            </p>
            <p className="mt-1 text-sm text-slate-600">Consulte uma fonte oficial por vez.</p>
          </div>
          <div
            className="inline-flex rounded-xl border border-slate-200 bg-white p-1 shadow-sm"
            role="group"
            aria-label="Fonte das votações"
          >
            {(["camara", "senado"] as const).map((item) => (
              <button
                key={item}
                type="button"
                aria-pressed={source === item}
                onClick={() => changeSource(item)}
                className={`min-h-11 rounded-lg px-4 text-sm font-bold transition ${
                  source === item
                    ? "bg-[#07152d] text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"
                }`}
              >
                {item === "camara" ? "Câmara" : "Senado"}
              </button>
            ))}
          </div>
        </div>

        <Card className="mt-6 p-5 shadow-sm sm:p-6">
          <form
            onSubmit={submitSearch}
            className="grid gap-4 lg:grid-cols-[minmax(250px,1.5fr)_repeat(4,minmax(140px,0.65fr))_auto]"
          >
            <label>
              <span className="mb-2 block text-sm font-bold text-slate-800">Buscar</span>
              <input
                type="search"
                value={draftSearch}
                onChange={(event) => setDraftSearch(event.target.value)}
                placeholder="Projeto, tema ou descrição"
                className="min-h-11 w-full rounded-xl border border-slate-300 px-4 text-sm outline-none placeholder:text-slate-400 focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
              />
            </label>
            <div>
              <span className="mb-2 block text-sm font-bold text-slate-800">Ano</span>
              <FilterSelect
                id="votings-year"
                label="Filtrar votações por ano"
                value={year}
                placeholder="Todos"
                options={(data?.facets.years ?? []).map(String)}
                onChange={(value) => {
                  setYear(value);
                  setPage(1);
                }}
              />
            </div>
            <div>
              <span className="mb-2 block text-sm font-bold text-slate-800">Resultado</span>
              <FilterSelect
                id="votings-result"
                label="Filtrar votações por resultado"
                value={result}
                placeholder="Todos"
                options={[
                  { value: "approved", label: "Aprovada" },
                  { value: "rejected", label: "Rejeitada" },
                  { value: "unknown", label: "Não informado" },
                ]}
                onChange={(value) => {
                  setResult(value as typeof result);
                  setPage(1);
                }}
              />
            </div>
            <div>
              <span className="mb-2 block text-sm font-bold text-slate-800">Modalidade</span>
              <FilterSelect
                id="votings-mode"
                label="Filtrar votações por modalidade"
                value={mode}
                placeholder="Todas"
                options={[
                  { value: "nominal", label: "Nominal" },
                  { value: "unknown", label: "Não identificada" },
                ]}
                onChange={(value) => {
                  setMode(value as typeof mode);
                  setPage(1);
                }}
              />
            </div>
            <div>
              <span className="mb-2 block text-sm font-bold text-slate-800">Ordenar</span>
              <FilterSelect
                id="votings-order"
                label="Ordenar votações"
                value={order}
                placeholder="Mais recentes"
                placeholderValue="newest"
                options={[{ value: "oldest", label: "Mais antigas" }]}
                onChange={(value) => {
                  setOrder(value as typeof order);
                  setPage(1);
                }}
              />
            </div>
            <Button type="submit" className="self-end">
              Pesquisar
            </Button>
          </form>
          {hasFilters && (
            <div className="mt-4 flex items-center border-t border-slate-100 pt-4">
              <p className="text-sm text-slate-500">A consulta possui filtros ativos.</p>
              <button
                type="button"
                onClick={resetFilters}
                className="ml-auto min-h-10 rounded-lg px-3 text-sm font-bold text-emerald-800 hover:bg-emerald-50"
              >
                Limpar filtros
              </button>
            </div>
          )}
        </Card>

        <div className="mt-10 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">
              {source === "camara" ? "Câmara dos Deputados" : "Senado Federal"}
            </p>
            <h2 className="mt-2 text-3xl font-bold text-slate-950">Resultados da consulta</h2>
          </div>
          <p className="text-sm text-slate-500" aria-live="polite">
            {loading ? "Atualizando…" : recordsLabel(data?.total ?? 0)}
          </p>
        </div>

        {error && (
          <Card className="mt-6 border-red-200 bg-red-50 p-6 text-red-900">
            <p className="font-bold">Não foi possível carregar a consulta.</p>
            <p className="mt-1 text-sm">{error}</p>
          </Card>
        )}
        {loading && !data && (
          <div className="mt-6 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="h-64 animate-pulse rounded-2xl bg-slate-200" />
            ))}
          </div>
        )}
        {!error && data && data.items.length > 0 && (
          <div
            className={`mt-6 grid gap-5 md:grid-cols-2 lg:grid-cols-3 ${loading ? "opacity-60" : ""}`}
          >
            {data.items.map((item) => {
              const resultMeta = resultLabel(item);
              return (
                <Link
                  key={item.id}
                  href={`/votacoes/${item.id}`}
                  className="group flex min-h-64 flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-bold ${resultMeta.style}`}
                    >
                      {resultMeta.label}
                    </span>
                    <span className="text-xs font-semibold text-slate-500">
                      {formatDate(item.occurred_on)}
                    </span>
                  </div>
                  <h3 className="mt-5 line-clamp-4 text-lg font-bold leading-7 text-slate-950">
                    {votingTitle(item)}
                  </h3>
                  <p className="mt-3 text-sm font-semibold text-slate-500">
                    {modeLabel(item.mode)}
                  </p>
                  <div className="mt-auto flex items-center justify-between border-t border-slate-100 pt-5 text-sm font-bold text-emerald-800">
                    <span>Entender a votação</span>
                    <span
                      className="transition-transform group-hover:translate-x-1"
                      aria-hidden="true"
                    >
                      →
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
        {!loading && !error && data?.items.length === 0 && (
          <Card className="mt-6 border-dashed p-10 text-center">
            <p className="text-xl font-bold text-slate-950">Nenhuma votação encontrada</p>
            <p className="mt-2 text-slate-600">Tente outra busca ou remova algum filtro.</p>
            <Button type="button" variant="secondary" className="mt-5" onClick={resetFilters}>
              Limpar filtros
            </Button>
          </Card>
        )}

        {data && (
          <LegislationPagination
            page={page}
            pageSize={PAGE_SIZE}
            total={data.total}
            onPageChange={(nextPage) => {
              setPage(nextPage);
              document.getElementById("conteudo")?.scrollIntoView({ behavior: "smooth" });
            }}
          />
        )}
      </section>
      <SiteFooter />
    </main>
  );
}
