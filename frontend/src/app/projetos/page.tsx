"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { FilterSelect } from "@/components/filter-select";
import { LegislationPagination } from "@/components/legislation-pagination";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PropositionPage, searchPropositions } from "@/lib/api";

const PAGE_SIZE = 12;

function propositionLabel(kind: string, number: number | null, year: number | null) {
  const sequence = number ? ` ${number}` : "";
  const period = year && year > 0 ? `/${year}` : "";
  return `${kind}${sequence}${period}`;
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

function recordsLabel(total: number) {
  return `${total.toLocaleString("pt-BR")} ${total === 1 ? "registro" : "registros"}`;
}

export default function ProjetosPage() {
  const [source, setSource] = useState<"camara" | "senado">("camara");
  const [draftSearch, setDraftSearch] = useState("");
  const [search, setSearch] = useState("");
  const [year, setYear] = useState("");
  const [kind, setKind] = useState("");
  const [order, setOrder] = useState<"newest" | "oldest" | "number_asc" | "number_desc">("newest");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PropositionPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void searchPropositions({
      source,
      q: search,
      year,
      kind,
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
            exception instanceof Error ? exception.message : "Não foi possível carregar projetos.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [source, search, year, kind, order, page]);

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setSearch(draftSearch.trim());
  }

  function resetFilters() {
    setDraftSearch("");
    setSearch("");
    setYear("");
    setKind("");
    setOrder("newest");
    setPage(1);
  }

  function changeSource(nextSource: "camara" | "senado") {
    setSource(nextSource);
    setYear("");
    setKind("");
    setPage(1);
  }

  const hasFilters = Boolean(search || year || kind || order !== "newest");
  const sourceLabel = source === "camara" ? "Câmara dos Deputados" : "Senado Federal";

  return (
    <main className="min-h-screen bg-[var(--paper)]">
      <SiteHeader />
      <section id="conteudo" tabIndex={-1} className="bg-[#07152d] text-white">
        <div className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:py-18">
          <div className="grid items-end gap-8 lg:grid-cols-[1fr_auto]">
            <div>
              <p className="text-sm font-bold tracking-[0.16em] text-emerald-300">Legislativo</p>
              <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl">
                Projetos e proposições
              </h1>
              <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-300">
                Pesquise a pauta legislativa, consulte autoria e tramitação e leia o texto oficial
                antes de formar sua opinião.
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
            aria-label="Fonte dos projetos"
          >
            {(["camara", "senado"] as const).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => changeSource(item)}
                aria-pressed={source === item}
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
            className="grid gap-4 lg:grid-cols-[minmax(260px,1.6fr)_repeat(3,minmax(150px,0.7fr))_auto]"
          >
            <label className="block">
              <span className="mb-2 block text-sm font-bold text-slate-800">Buscar</span>
              <input
                type="search"
                value={draftSearch}
                onChange={(event) => setDraftSearch(event.target.value)}
                placeholder="Número, tipo ou palavra da ementa"
                className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-4 text-sm outline-none placeholder:text-slate-400 focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
              />
            </label>
            <div>
              <span className="mb-2 block text-sm font-bold text-slate-800">Ano</span>
              <FilterSelect
                id="projects-year"
                label="Filtrar projetos por ano"
                value={year}
                placeholder="Todos os anos"
                options={(data?.facets.years ?? []).map(String)}
                onChange={(value) => {
                  setYear(value);
                  setPage(1);
                }}
              />
            </div>
            <div>
              <span className="mb-2 block text-sm font-bold text-slate-800">Tipo</span>
              <FilterSelect
                id="projects-kind"
                label="Filtrar projetos por tipo"
                value={kind}
                placeholder="Todos os tipos"
                options={data?.facets.kinds ?? []}
                onChange={(value) => {
                  setKind(value);
                  setPage(1);
                }}
              />
            </div>
            <div>
              <span className="mb-2 block text-sm font-bold text-slate-800">Ordenar</span>
              <FilterSelect
                id="projects-order"
                label="Ordenar projetos"
                value={order}
                placeholder="Mais recentes"
                placeholderValue="newest"
                options={[
                  { value: "oldest", label: "Mais antigos" },
                  { value: "number_asc", label: "Menor número" },
                  { value: "number_desc", label: "Maior número" },
                ]}
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
            <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
              <span className="text-sm text-slate-500">Filtros ativos</span>
              {search && <Badge>Busca: {search}</Badge>}
              {year && <Badge>Ano: {year}</Badge>}
              {kind && <Badge>Tipo: {kind}</Badge>}
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

        <div className="mt-10 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">
              {sourceLabel}
            </p>
            <h2 className="mt-2 text-3xl font-bold text-slate-950">Resultados da consulta</h2>
          </div>
          <p className="text-sm text-slate-500" aria-live="polite">
            {loading ? "Atualizando resultados…" : recordsLabel(data?.total ?? 0)}
          </p>
        </div>

        {error && (
          <Card className="mt-6 border-red-200 bg-red-50 p-6 text-red-900">
            <p className="font-bold">Não foi possível carregar a consulta.</p>
            <p className="mt-1 text-sm">{error}</p>
          </Card>
        )}

        {loading && !data && (
          <div
            className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3"
            aria-label="Carregando projetos"
          >
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="h-64 animate-pulse rounded-2xl bg-slate-200" />
            ))}
          </div>
        )}

        {!error && data && data.items.length > 0 && (
          <div
            className={`mt-6 grid gap-5 md:grid-cols-2 lg:grid-cols-3 ${loading ? "opacity-60" : ""}`}
          >
            {data.items.map((item) => (
              <Link
                key={item.id}
                href={`/proposicoes/${item.id}`}
                className="group flex min-h-64 flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700"
              >
                <div className="flex items-start justify-between gap-4">
                  <Badge>{propositionLabel(item.kind, item.number, item.year)}</Badge>
                  <span className="text-xs font-semibold text-slate-500">
                    {formatDate(item.presented_at)}
                  </span>
                </div>
                <h3 className="mt-5 line-clamp-5 text-lg font-bold leading-7 text-slate-950">
                  {item.summary || "Ementa ainda não importada"}
                </h3>
                <div className="mt-auto flex items-center justify-between border-t border-slate-100 pt-5 text-sm font-bold text-emerald-800">
                  <span>Ver ficha completa</span>
                  <span
                    className="transition-transform group-hover:translate-x-1"
                    aria-hidden="true"
                  >
                    →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}

        {!loading && !error && data?.items.length === 0 && (
          <Card className="mt-6 border-dashed p-10 text-center">
            <p className="text-xl font-bold text-slate-950">Nenhum projeto encontrado</p>
            <p className="mx-auto mt-2 max-w-lg text-slate-600">
              Tente outra palavra ou remova um dos filtros da consulta.
            </p>
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
