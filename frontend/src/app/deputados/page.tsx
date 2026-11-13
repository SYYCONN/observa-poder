"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { fetchParliamentarianParties, fetchParliamentarians, Parliamentarian } from "@/lib/api";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { FilterSelect } from "@/components/filter-select";

const states = [
  "AC",
  "AL",
  "AP",
  "AM",
  "BA",
  "CE",
  "DF",
  "ES",
  "GO",
  "MA",
  "MT",
  "MS",
  "MG",
  "PA",
  "PB",
  "PR",
  "PE",
  "PI",
  "RJ",
  "RN",
  "RS",
  "RO",
  "RR",
  "SC",
  "SP",
  "SE",
  "TO",
];
const COLUMN_SIZE = 10;
const PAGE_SIZE = COLUMN_SIZE * 2;
type DeputyStatus = "" | "Históricos" | "Todos os registros";

function apiStatus(status: DeputyStatus): "current" | "historical" | "all" {
  if (status === "Históricos") return "historical";
  if (status === "Todos os registros") return "all";
  return "current";
}

function formatCollectedAt(value: string | undefined) {
  if (!value) return "Data não informada";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Data não informada" : date.toLocaleString("pt-BR");
}

function PersonMark({ person }: { person: Parliamentarian }) {
  const [photoFailed, setPhotoFailed] = useState(false);
  const photoTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const initials = person.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  useEffect(() => {
    setPhotoFailed(false);
    if (!person.photo_url) return;
    photoTimeout.current = setTimeout(() => setPhotoFailed(true), 3500);
    return () => {
      if (photoTimeout.current) clearTimeout(photoTimeout.current);
    };
  }, [person.id, person.photo_url]);

  return (
    <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-emerald-50 text-sm font-semibold text-emerald-800">
      {person.photo_url && !photoFailed ? (
        <img
          src={person.photo_url}
          alt=""
          className="h-full w-full object-cover"
          onLoad={() => {
            if (photoTimeout.current) clearTimeout(photoTimeout.current);
          }}
          onError={() => setPhotoFailed(true)}
        />
      ) : (
        initials
      )}
    </div>
  );
}

export default function DeputadosPage() {
  const [search, setSearch] = useState("");
  const [state, setState] = useState("");
  const [party, setParty] = useState("");
  const [status, setStatus] = useState<DeputyStatus>("");
  const [parties, setParties] = useState<string[]>([]);
  const [people, setPeople] = useState<Parliamentarian[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(params = { search, state, party, status }, nextPage = page) {
    setLoading(true);
    setError("");
    try {
      const result = await fetchParliamentarians({
        ...params,
        status: apiStatus(params.status),
        limit: PAGE_SIZE,
        offset: nextPage * PAGE_SIZE,
      });
      setPeople(result.items);
      setTotal(result.total);
      setPage(nextPage);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Falha ao carregar deputados.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load({ search: "", state: "", party: "", status: "" });
    void fetchParliamentarianParties()
      .then(setParties)
      .catch(() => setParties([]));
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    void load({ search, state, party, status }, 0);
  }

  function clearFilters() {
    setSearch("");
    setState("");
    setParty("");
    setStatus("");
    void load({ search: "", state: "", party: "", status: "" }, 0);
  }

  function goToPage(nextPage: number) {
    if (nextPage < 0 || nextPage >= Math.ceil(total / PAGE_SIZE)) return;
    void load({ search, state, party, status }, nextPage);
  }

  const collectedAt = useMemo(
    () =>
      people
        .map((person) => person.collected_at)
        .filter(Boolean)
        .sort()
        .at(-1),
    [people],
  );
  const columns = [people.slice(0, COLUMN_SIZE), people.slice(COLUMN_SIZE, PAGE_SIZE)].filter(
    (column) => column.length > 0,
  );

  return (
    <main className="min-h-screen bg-[var(--paper)]">
      <SiteHeader />
      <section
        id="conteudo"
        tabIndex={-1}
        className="relative isolate overflow-hidden border-b border-[#102a50] bg-[#07152d] text-white"
      >
        <img
          src="/hero/camara.png"
          alt=""
          aria-hidden="true"
          className="absolute inset-0 -z-20 h-full w-full object-cover object-center opacity-35"
        />
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-[#07152d]/95 via-[#07152d]/80 to-[#07152d]/55" />
        <div className="mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:py-16">
          <p className="text-sm font-semibold tracking-[0.08em] text-emerald-300">
            Representantes · Câmara dos Deputados
          </p>
          <div className="mt-3 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-4xl font-semibold tracking-[-0.03em] text-white sm:text-5xl">
                Deputados federais
              </h1>
              <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-200">
                Consulte quem ocupa uma cadeira na Câmara, seu partido, estado e registro oficial.
              </p>
            </div>
            <p className="text-sm text-slate-300">Fonte: Câmara dos Deputados</p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-14">
        <form onSubmit={submit} className="border-y border-slate-200 bg-white px-5 py-5 sm:px-6">
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_150px_180px_180px_auto]">
            <label className="sr-only" htmlFor="deputy-search">
              Buscar deputado por nome ou identificador
            </label>
            <input
              id="deputy-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por nome ou identificador"
              className="min-h-11 rounded border border-slate-300 px-4 text-sm text-[#07152d] outline-none placeholder:text-slate-400 focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
            />
            <FilterSelect
              id="deputy-state"
              label="Filtrar deputados por estado"
              value={state}
              placeholder="Todos os estados"
              options={states}
              onChange={setState}
            />
            <FilterSelect
              id="deputy-party"
              label="Filtrar deputados por partido"
              value={party}
              placeholder="Todos os partidos"
              options={parties}
              onChange={setParty}
            />
            <FilterSelect
              id="deputy-status"
              label="Filtrar deputados por situação"
              value={status}
              placeholder="Em exercício"
              options={["Históricos", "Todos os registros"]}
              onChange={(value) => setStatus(value as DeputyStatus)}
            />
            <button
              type="submit"
              className="min-h-11 rounded bg-[#07152d] px-6 text-sm font-semibold text-white hover:bg-[#102a50] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700"
            >
              Pesquisar
            </button>
          </div>
          {(search || state || party || status) && (
            <button
              type="button"
              onClick={clearFilters}
              className="mt-3 text-sm font-semibold text-emerald-800 underline decoration-emerald-300 underline-offset-4 hover:text-[#07152d]"
            >
              Limpar filtros
            </button>
          )}
        </form>

        <div className="mt-10 flex flex-col gap-2 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold tracking-[0.08em] text-emerald-700">
              Registro nominal
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-[#07152d]">
              {status === ""
                ? "Deputados em exercício"
                : status === "Históricos"
                  ? "Registros históricos"
                  : "Deputados atuais e históricos"}
            </h2>
          </div>
          <div className="text-sm text-slate-500 sm:text-right">
            <p aria-live="polite">{loading ? "Carregando registros…" : `${total} encontrados`}</p>
            {!loading && collectedAt && (
              <p className="mt-1 text-xs">Coleta mais recente: {formatCollectedAt(collectedAt)}</p>
            )}
          </div>
        </div>

        {error && (
          <div
            className="mt-6 border border-red-200 bg-red-50 p-4 text-sm text-red-800"
            role="alert"
          >
            {error}
          </div>
        )}
        {loading && (
          <div
            className="divide-y divide-slate-200 border-b border-slate-200 bg-white"
            aria-label="Carregando deputados"
            aria-busy="true"
          >
            {[1, 2, 3, 4].map((item) => (
              <div key={item} className="h-20 animate-pulse bg-slate-50/70" />
            ))}
          </div>
        )}
        {!loading && !error && people.length === 0 && (
          <div className="border-b border-slate-200 bg-white px-5 py-12 text-center">
            <p className="font-semibold text-[#07152d]">Nenhum deputado encontrado.</p>
            <p className="mt-2 text-sm text-slate-500">
              Tente outro nome, identificador, estado ou partido.
            </p>
          </div>
        )}

        {!loading && people.length > 0 && (
          <>
            <div className="grid gap-4 lg:grid-cols-2">
              {columns.map((column, columnIndex) => (
                <div
                  key={`deputy-column-${columnIndex}`}
                  className="overflow-hidden border-b border-slate-200 bg-white lg:border"
                >
                  <div
                    className="hidden grid-cols-[minmax(0,1fr)_112px_48px_48px_96px] gap-3 border-b border-slate-200 px-4 py-3 text-[11px] font-semibold tracking-[0.06em] text-slate-500 sm:grid"
                    role="row"
                  >
                    <span>Parlamentar</span>
                    <span>Partido</span>
                    <span>UF</span>
                    <span>Leg.</span>
                    <span className="text-right">Perfil</span>
                  </div>
                  {column.map((person) => (
                    <article
                      key={person.id}
                      className="grid gap-3 border-b border-slate-200 px-4 py-4 last:border-b-0 sm:grid-cols-[minmax(0,1fr)_112px_48px_48px_96px] sm:items-center"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <PersonMark person={person} />
                        <div className="min-w-0">
                          <h3 className="truncate font-semibold text-[#07152d]">{person.name}</h3>
                          <p className="mt-1 text-xs text-slate-500">ID {person.external_id}</p>
                          {!person.is_current && (
                            <span className="mt-1 inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
                              Registro histórico
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="min-w-0">
                        <span className="text-xs text-slate-500 sm:hidden">Partido · </span>
                        <span
                          className="block truncate text-sm text-slate-700"
                          title={person.party ?? "Não informado"}
                        >
                          {person.party ?? "Não informado"}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-slate-500 sm:hidden">UF · </span>
                        <span className="text-sm font-semibold text-[#07152d]">
                          {person.state ?? "—"}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-slate-500 sm:hidden">Legislatura · </span>
                        <span className="text-sm text-slate-700">
                          {person.legislature ?? "Não informada"}
                        </span>
                      </div>
                      <Link
                        href={`/parlamentares/${person.id}`}
                        className="text-sm font-semibold text-emerald-800 hover:text-[#07152d] hover:underline sm:text-right"
                      >
                        Ver perfil →
                      </Link>
                    </article>
                  ))}
                </div>
              ))}
            </div>
            <nav
              className="flex flex-col gap-3 border-b border-slate-200 bg-white px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6"
              aria-label="Paginação de deputados"
            >
              <p className="text-sm text-slate-500">
                Página {page + 1} de {Math.max(1, Math.ceil(total / PAGE_SIZE))}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => goToPage(page - 1)}
                  disabled={page === 0 || loading}
                  className="rounded border border-slate-300 px-4 py-2 text-sm font-semibold text-[#07152d] transition hover:border-emerald-700 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Anterior
                </button>
                <button
                  type="button"
                  onClick={() => goToPage(page + 1)}
                  disabled={page >= Math.ceil(total / PAGE_SIZE) - 1 || loading}
                  className="rounded border border-slate-300 px-4 py-2 text-sm font-semibold text-[#07152d] transition hover:border-emerald-700 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Próxima
                </button>
              </div>
            </nav>
          </>
        )}
      </section>
      <SiteFooter />
    </main>
  );
}
