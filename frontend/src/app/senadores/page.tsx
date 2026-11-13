"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { FilterSelect } from "@/components/filter-select";
import { SiteFooter, SiteHeader } from "@/components/site-header";
import { fetchParliamentarianParties, fetchParliamentarians, Parliamentarian } from "@/lib/api";

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
const statusLabels = {
  current: "Senadores em exercício",
  historical: "Registros históricos",
  all: "Senadores atuais e históricos",
} as const;
type Status = keyof typeof statusLabels;
const initialFilters = { search: "", state: "", party: "", status: "current" as Status };

function formatCollectedAt(value: number) {
  return new Date(value).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
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

export default function SenadoresPage() {
  const [search, setSearch] = useState("");
  const [state, setState] = useState("");
  const [party, setParty] = useState("");
  const [parties, setParties] = useState<string[]>([]);
  const [partyUnavailable, setPartyUnavailable] = useState(false);
  const [status, setStatus] = useState<Status>("current");
  const [appliedFilters, setAppliedFilters] = useState(initialFilters);
  const requestId = useRef(0);
  const [people, setPeople] = useState<Parliamentarian[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(params = initialFilters, nextPage = 0) {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError("");
    try {
      const result = await fetchParliamentarians({
        ...params,
        source: "senado",
        limit: PAGE_SIZE,
        offset: nextPage * PAGE_SIZE,
      });
      if (currentRequest !== requestId.current) return;
      setAppliedFilters(params);
      setPeople(result.items);
      setTotal(result.total);
      setPage(nextPage);
    } catch {
      if (currentRequest !== requestId.current) return;
      setPeople([]);
      setTotal(0);
      setError("Não foi possível carregar os senadores. Tente novamente.");
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    void fetchParliamentarianParties("senado")
      .then(setParties)
      .catch(() => setPartyUnavailable(true));
    return () => {
      requestId.current += 1;
    };
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    void load({ search: search.trim(), state, party, status }, 0);
  }

  function clearFilters() {
    setSearch("");
    setState("");
    setParty("");
    setStatus("current");
    void load(initialFilters);
  }

  function goToPage(nextPage: number) {
    if (nextPage < 0 || nextPage >= Math.ceil(total / PAGE_SIZE)) return;
    void load(appliedFilters, nextPage);
  }

  const collectedAt = Math.max(
    ...people.map((person) => Date.parse(person.collected_at)).filter(Number.isFinite),
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
          src="/hero/senado.png"
          alt=""
          aria-hidden="true"
          className="absolute inset-0 -z-20 h-full w-full object-cover object-center opacity-35"
        />
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-[#07152d]/95 via-[#07152d]/80 to-[#07152d]/55" />
        <div className="mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:py-16">
          <p className="text-sm font-semibold tracking-[0.08em] text-emerald-300">
            Representantes · Senado Federal
          </p>
          <div className="mt-3 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-4xl font-semibold tracking-[-0.03em] text-white sm:text-5xl">
                Senadores
              </h1>
              <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-200">
                Consulte senadores em exercício e registros históricos coletados do Senado Federal.
              </p>
            </div>
            <p className="text-sm text-slate-300">Fonte: Senado Federal</p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-14">
        <form onSubmit={submit} className="border-y border-slate-200 bg-white px-5 py-5 sm:px-6">
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_150px_180px_180px_auto]">
            <label className="sr-only" htmlFor="senator-search">
              Buscar senador por nome ou identificador
            </label>
            <input
              id="senator-search"
              maxLength={100}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por nome ou identificador"
              className="min-h-11 rounded border border-slate-300 px-4 text-sm text-[#07152d] outline-none placeholder:text-slate-400 focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
            />
            <FilterSelect
              id="senator-state"
              label="Filtrar senadores por estado"
              value={state}
              placeholder="Todos os estados"
              options={states}
              onChange={setState}
            />
            <FilterSelect
              id="senator-party"
              label="Filtrar senadores por partido"
              value={party}
              placeholder="Todos os partidos"
              options={parties}
              onChange={setParty}
            />
            <FilterSelect
              id="senator-status"
              label="Filtrar senadores por situação"
              value={status === "current" ? "" : status}
              placeholder="Em exercício"
              options={[
                { value: "historical", label: "Históricos" },
                { value: "all", label: "Todos os registros" },
              ]}
              onChange={(value) =>
                setStatus(value === "historical" || value === "all" ? value : "current")
              }
            />
            <button
              type="submit"
              className="min-h-11 rounded bg-[#07152d] px-6 text-sm font-semibold text-white hover:bg-[#102a50] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700"
            >
              Pesquisar
            </button>
          </div>
          {(search || state || party || status !== "current") && (
            <button
              type="button"
              onClick={clearFilters}
              className="mt-3 text-sm font-semibold text-emerald-800 underline decoration-emerald-300 underline-offset-4 hover:text-[#07152d]"
            >
              Limpar filtros
            </button>
          )}
        </form>
        {partyUnavailable && (
          <p role="status" className="mt-2 text-sm text-slate-600">
            O filtro por partido está indisponível. Você ainda pode buscar por nome, UF e situação.
          </p>
        )}

        <div className="mt-10 flex flex-col gap-2 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold tracking-[0.08em] text-emerald-700">
              Registro nominal
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-[#07152d]">
              {statusLabels[appliedFilters.status]}
            </h2>
            {appliedFilters.status !== "current" && (
              <p className="mt-2 text-sm text-slate-600">
                O histórico reúne pessoas observadas nas coletas do portal.
              </p>
            )}
          </div>
          <div className="text-sm text-slate-500 sm:text-right">
            {!error && (
              <p role="status">
                {loading
                  ? "Carregando registros…"
                  : total === 1
                    ? "1 senador encontrado"
                    : `${total} encontrados`}
              </p>
            )}
            {!loading && Number.isFinite(collectedAt) && (
              <p className="mt-1 text-xs">
                Coleta mais recente:{" "}
                <time dateTime={new Date(collectedAt).toISOString()}>
                  {formatCollectedAt(collectedAt)}
                </time>
              </p>
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
            aria-label="Carregando senadores"
            aria-busy="true"
          >
            {[1, 2, 3, 4].map((item) => (
              <div key={item} className="h-20 animate-pulse bg-slate-50/70" />
            ))}
          </div>
        )}
        {!loading && !error && people.length === 0 && (
          <div role="status" className="border-b border-slate-200 bg-white px-5 py-12 text-center">
            <p className="font-semibold text-[#07152d]">Nenhum senador encontrado.</p>
            <p className="mt-2 text-sm text-slate-500">
              Tente outro nome, identificador, estado, partido ou situação.
            </p>
          </div>
        )}

        {!loading && people.length > 0 && (
          <>
            <div className="grid gap-4 lg:grid-cols-2">
              {columns.map((column, columnIndex) => (
                <div
                  key={`senator-column-${columnIndex}`}
                  className="overflow-hidden border-b border-slate-200 bg-white lg:border"
                >
                  <div
                    className="hidden grid-cols-[minmax(0,1fr)_112px_48px_48px_96px] gap-3 border-b border-slate-200 px-4 py-3 text-[11px] font-semibold tracking-[0.06em] text-slate-500 sm:grid"
                    aria-hidden="true"
                  >
                    <span>Parlamentar</span>
                    <span>Partido</span>
                    <span>UF</span>
                    <span title="Legislatura">Leg.</span>
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
                          <h3 className="truncate font-semibold text-[#07152d]" title={person.name}>
                            {person.name}
                          </h3>
                          <p className="mt-1 text-xs text-slate-500">ID {person.external_id}</p>
                          {!person.is_current && (
                            <span className="mt-1 inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
                              Registro histórico
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="min-w-0">
                        <span className="text-xs text-slate-500 sm:sr-only">Partido · </span>
                        <span
                          className="block truncate text-sm text-slate-700"
                          title={person.party ?? "Não informado"}
                        >
                          {person.party ?? "Não informado"}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-slate-500 sm:sr-only">UF · </span>
                        <span className="text-sm font-semibold text-[#07152d]">
                          {person.state ?? "—"}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-slate-500 sm:sr-only">Legislatura · </span>
                        <span className="text-sm text-slate-700">
                          {person.legislature ?? "Não informada"}
                        </span>
                      </div>
                      <Link
                        href={`/parlamentares/${person.id}`}
                        aria-label={`Ver perfil de ${person.name}`}
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
              aria-label="Paginação de senadores"
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
