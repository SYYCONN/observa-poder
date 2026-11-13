"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { FilterSelect } from "@/components/filter-select";

type Detail = {
  name: string;
  external_id: string;
  photo_url: string | null;
  state: string | null;
  party: string | null;
  legislature: string | null;
  source_url: string;
  source: "camara" | "senado";
  collected_at: string;
  is_current: boolean;
  birth_date: string | null;
  profile_source_url: string | null;
  election_votes: number | null;
  election_year: number | null;
  election_status: string | null;
  election_source_url: string | null;
  mandate_started_on: string | null;
  mandate_ended_on: string | null;
  mandates: {
    legislature: string;
    state: string;
    party: string | null;
    source_url: string;
    started_on: string | null;
    ended_on: string | null;
    collected_at: string;
  }[];
  authored_propositions: {
    id: string;
    label: string;
    summary: string;
    presented_at: string | null;
    source_url: string;
  }[];
  authored_propositions_total: number;
  vote_records: {
    voting_id: string;
    occurred_on: string | null;
    description: string;
    object_description: string | null;
    position: string;
    party_at_vote: string | null;
    state_at_vote: string | null;
    source_url: string;
  }[];
  financial_summary: {
    available: boolean;
    year_from: number | null;
    year: number | null;
    expense_count: number;
    net_total: number | string | null;
    glossed_total: number | string | null;
    source_url: string | null;
    expense_source: string | null;
    expense_collected_at: string | null;
    subsidy_reference: number | string | null;
    subsidy_source_url: string | null;
    subsidy_note: string | null;
    remuneration_year: number | null;
    remuneration_month: number | null;
    remuneration_fixed: number | string | null;
    remuneration_net: number | string | null;
    remuneration_source_url: string | null;
    remuneration_source: string | null;
    remuneration_collected_at: string | null;
    staff_count: number | null;
    staff_year: number | null;
    staff_month: number | null;
    staff_source_url: string | null;
    staff_source: string | null;
    staff_collected_at: string | null;
    amendment_year: number | null;
    amendment_count: number | null;
    amendment_committed: number | string | null;
    amendment_liquidated: number | string | null;
    amendment_paid: number | string | null;
    amendment_source_url: string | null;
    amendment_source: string | null;
    amendment_collected_at: string | null;
  };
  votes_total: number;
  votes_by_position: Record<string, number>;
};

type FinancialExpense = {
  id: string;
  external_id: string;
  year: number;
  occurred_on: string | null;
  month: number | null;
  category: string;
  category_detail: string | null;
  supplier_name: string | null;
  document_number: string | null;
  document_type: string | null;
  amount_document: number | string | null;
  amount_glossed: number | string | null;
  amount_net: number | string | null;
  reimbursement: string | null;
  source_document_url: string | null;
  source: string;
  source_url: string;
  collected_at: string;
  source_record_id: string;
};

type FinancialExpensePage = {
  items: FinancialExpense[];
  total: number;
  limit: number;
  offset: number;
  year: number | null;
};

type StaffMember = {
  id: string;
  external_id: string;
  name: string;
  category: string | null;
  area_of_work: string | null;
  job_title: string | null;
  level: string | null;
  gross_amount: number | string | null;
  net_amount: number | string | null;
  allowances_amount: number | string | null;
  source_query_url: string;
  source_remuneration_url: string | null;
  payroll_type: string | null;
  exercise_date: string | null;
  source: string;
  source_url: string;
  collected_at: string;
  source_record_id: string;
};

type StaffPage = {
  items: StaffMember[];
  total: number;
  limit: number;
  offset: number;
  year: number | null;
  month: number | null;
  source: string | null;
  source_url: string | null;
  collected_at: string | null;
  source_record_id: string | null;
};

type AuthoredPropositionPage = {
  items: Detail["authored_propositions"];
  total: number;
  limit: number;
  offset: number;
};

type VoteRecordPage = {
  items: Detail["vote_records"];
  total: number;
  limit: number;
  offset: number;
};

type FinancialPeriodMode = "year" | "month" | "exact" | "range";

type FinancialPeriodFilters = {
  mode: FinancialPeriodMode;
  year: string;
  month: string;
  date: string;
  dateFrom: string;
  dateTo: string;
};

const financialPeriodLabels: Record<FinancialPeriodMode, string> = {
  year: "Ano inteiro",
  month: "Mês",
  exact: "Data exata",
  range: "Intervalo de datas",
};
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const partyAssets: Record<string, string> = {
  AGIR: "agir",
  AVANTE: "avante",
  CIDADANIA: "cidadania",
  MDB: "mdb",
  MISSÃO: "missao",
  NOVO: "novo",
  PCdoB: "pcdob",
  PDT: "pdt",
  PL: "pl",
  PODE: "podemos",
  PP: "pp",
  PRD: "prd",
  PSB: "psb",
  PSD: "psd",
  PSDB: "psdb",
  PSOL: "psol",
  PT: "pt",
  PV: "pv",
  REDE: "rede",
  REPUBLICANOS: "republicanos",
  SOLIDARIEDADE: "soliedariedade",
  UNIÃO: "uniao",
};

const partyNames: Record<string, string> = {
  AGIR: "Agir",
  AVANTE: "Avante",
  CIDADANIA: "Cidadania",
  MDB: "Movimento Democrático Brasileiro",
  MISSÃO: "Missão",
  NOVO: "Partido Novo",
  PCdoB: "Partido Comunista do Brasil",
  PDT: "Partido Democrático Trabalhista",
  PL: "Partido Liberal",
  PODE: "Podemos",
  PP: "Progressistas",
  PRD: "Partido da Renovação Democrática",
  PSB: "Partido Socialista Brasileiro",
  PSD: "Partido Social Democrático",
  PSDB: "Partido da Social Democracia Brasileira",
  PSOL: "Partido Socialismo e Liberdade",
  PT: "Partido dos Trabalhadores",
  PV: "Partido Verde",
  REDE: "Rede Sustentabilidade",
  REPUBLICANOS: "Republicanos",
  SOLIDARIEDADE: "Solidariedade",
  UNIÃO: "União Brasil",
};

const partyColors: Record<string, string> = {
  AGIR: "#e51b23",
  AVANTE: "#f58220",
  CIDADANIA: "#ef6c2e",
  MDB: "#0084b4",
  MISSÃO: "#6b3fa0",
  NOVO: "#f58220",
  PCdoB: "#d71920",
  PDT: "#e31b23",
  PL: "#1f4f91",
  PODE: "#f2a900",
  PP: "#1769aa",
  PRD: "#159a9c",
  PSB: "#f15a29",
  PSD: "#f28c00",
  PSDB: "#1e5aa8",
  PSOL: "#f28c00",
  PT: "#d71920",
  PV: "#008c45",
  REDE: "#ec1c24",
  REPUBLICANOS: "#008b4f",
  SOLIDARIEDADE: "#f58220",
  UNIÃO: "#1b4d91",
};

function PartyMark({ party }: { party: string | null }) {
  const asset = party ? partyAssets[party] : undefined;
  const name = party ? (partyNames[party] ?? party) : "Partido não informado";
  const color = party ? (partyColors[party] ?? "#54d6b5") : "#54d6b5";
  const accent = `color-mix(in srgb, ${color} 42%, white)`;
  return (
    <div className="flex shrink-0 flex-col items-center gap-2 text-center" title={name}>
      <div
        className="flex h-24 w-24 items-center justify-center rounded-full border-2 bg-white p-3 shadow-lg"
        style={{ borderColor: color }}
      >
        {asset ? (
          <img
            src={`/partidos/${asset}.svg`}
            alt={`Símbolo do partido ${name}`}
            className="max-h-full max-w-full object-contain"
          />
        ) : (
          <span className="text-sm font-bold text-slate-700">—</span>
        )}
      </div>
      <span className="max-w-32 text-xs font-semibold leading-4" style={{ color: accent }}>
        {name}
      </span>
    </div>
  );
}

export default function ParliamentarianPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [person, setPerson] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [showFinancialSource, setShowFinancialSource] = useState(false);
  const [showStaff, setShowStaff] = useState(false);
  const [staffPage, setStaffPage] = useState<StaffPage | null>(null);
  const [staffLoading, setStaffLoading] = useState(false);
  const [staffError, setStaffError] = useState("");
  const [projectsExpanded, setProjectsExpanded] = useState(false);
  const [projectsPage, setProjectsPage] = useState<AuthoredPropositionPage | null>(null);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [projectsError, setProjectsError] = useState("");
  const [votesPage, setVotesPage] = useState<VoteRecordPage | null>(null);
  const [votesLoading, setVotesLoading] = useState(false);
  const [votesError, setVotesError] = useState("");
  const [financialExpensesPage, setFinancialExpensesPage] = useState<FinancialExpensePage | null>(
    null,
  );
  const [financialExpensesLoading, setFinancialExpensesLoading] = useState(false);
  const [financialExpensesError, setFinancialExpensesError] = useState("");
  const [financialPeriod, setFinancialPeriod] = useState<FinancialPeriodFilters>({
    mode: "year",
    year: "",
    month: "",
    date: "",
    dateFrom: "",
    dateTo: "",
  });
  const [appliedFinancialPeriod, setAppliedFinancialPeriod] =
    useState<FinancialPeriodFilters>(financialPeriod);
  const [financialFilterError, setFinancialFilterError] = useState("");
  const [photoFailed, setPhotoFailed] = useState(false);
  const photoTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    setPhotoFailed(false);
    if (photoTimeout.current) clearTimeout(photoTimeout.current);
    fetch(`${API_URL}/parliamentarians/${params.id}`)
      .then((response) =>
        response.ok ? response.json() : Promise.reject(new Error("Parlamentar não encontrado.")),
      )
      .then(setPerson)
      .catch((exception) => setError(exception.message));
  }, [params.id]);
  useEffect(() => {
    if (!person?.photo_url) return;
    photoTimeout.current = setTimeout(() => setPhotoFailed(true), 3500);
    return () => {
      if (photoTimeout.current) clearTimeout(photoTimeout.current);
    };
  }, [person?.photo_url]);
  useEffect(() => {
    if (!showFinancialSource && !showStaff) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setShowFinancialSource(false);
        setShowStaff(false);
      }
    };
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [showFinancialSource, showStaff]);
  useEffect(() => {
    if (!person?.financial_summary.year || financialPeriod.year) return;
    setFinancialPeriod((current) => ({
      ...current,
      year: String(person.financial_summary.year),
    }));
  }, [person?.financial_summary.year, financialPeriod.year]);
  const partyColor = person?.party ? (partyColors[person.party] ?? "#54d6b5") : "#54d6b5";
  const partyAccent = `color-mix(in srgb, ${partyColor} 42%, white)`;
  const personInitials = person?.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
  const authoredPropositions = projectsPage?.items ?? person?.authored_propositions ?? [];
  const voteRecords = votesPage?.items ?? person?.vote_records ?? [];
  const voteBreakdown = Object.entries(person?.votes_by_position ?? {});
  const formatDate = (value: string | null) =>
    value ? new Date(`${value}T12:00:00`).toLocaleDateString("pt-BR") : null;
  const formatCollectedAt = (value: string | null) =>
    value
      ? new Date(value).toLocaleString("pt-BR", {
          dateStyle: "short",
          timeStyle: "short",
          timeZone: "America/Sao_Paulo",
        })
      : "Coleta não informada";
  const ageFromBirthDate = (value: string | null) => {
    if (!value) return null;
    const [year, month, day] = value.split("-").map(Number);
    const today = new Date();
    let age = today.getFullYear() - year;
    if (today.getMonth() + 1 < month || (today.getMonth() + 1 === month && today.getDate() < day)) {
      age -= 1;
    }
    return age;
  };
  const formatCurrency = (value: number | string | null) => {
    if (value === null) return "Não coletado";
    const numericValue = typeof value === "number" ? value : Number(value);
    return Number.isFinite(numericValue)
      ? numericValue.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
      : "Não informado";
  };
  const loadFinancialExpenses = (offset = 0, filters = appliedFinancialPeriod) => {
    if (!person) return;
    setFinancialExpensesLoading(true);
    setFinancialExpensesError("");
    const query = new URLSearchParams({ limit: "10", offset: String(offset) });
    if (filters.mode === "year") {
      if (filters.year || person.financial_summary.year) {
        query.set("year", filters.year || String(person.financial_summary.year));
      }
    }
    if (filters.mode === "month" && filters.month) query.set("month", filters.month);
    if (filters.mode === "exact" && filters.date) query.set("date", filters.date);
    if (filters.mode === "range") {
      if (filters.dateFrom) query.set("date_from", filters.dateFrom);
      if (filters.dateTo) query.set("date_to", filters.dateTo);
    }
    fetch(`${API_URL}/parliamentarians/${params.id}/financial-expenses?${query}`)
      .then((response) =>
        response.ok
          ? response.json()
          : Promise.reject(new Error("Não foi possível carregar as despesas.")),
      )
      .then(setFinancialExpensesPage)
      .catch((exception) => setFinancialExpensesError(exception.message))
      .finally(() => setFinancialExpensesLoading(false));
  };
  const openFinancialSource = () => {
    setShowFinancialSource(true);
    if (!financialExpensesPage) loadFinancialExpenses();
  };
  const loadStaff = (offset = 0) => {
    setStaffLoading(true);
    setStaffError("");
    const query = new URLSearchParams({ limit: "10", offset: String(offset) });
    fetch(`${API_URL}/parliamentarians/${params.id}/staff?${query}`)
      .then((response) =>
        response.ok
          ? response.json()
          : Promise.reject(new Error("Não foi possível carregar a equipe.")),
      )
      .then(setStaffPage)
      .catch((exception) => setStaffError(exception.message))
      .finally(() => setStaffLoading(false));
  };
  const openStaff = () => {
    setShowStaff(true);
    if (!staffPage) loadStaff();
  };
  const loadProjects = (offset = 0) => {
    setProjectsLoading(true);
    setProjectsError("");
    fetch(`${API_URL}/parliamentarians/${params.id}/authored-propositions?limit=5&offset=${offset}`)
      .then((response) =>
        response.ok
          ? response.json()
          : Promise.reject(new Error("Não foi possível carregar os projetos.")),
      )
      .then(setProjectsPage)
      .catch((exception) => setProjectsError(exception.message))
      .finally(() => setProjectsLoading(false));
  };
  const expandProjects = () => {
    setProjectsExpanded(true);
    if (!projectsPage) loadProjects();
  };
  const loadVotes = (offset = 0) => {
    setVotesLoading(true);
    setVotesError("");
    fetch(`${API_URL}/parliamentarians/${params.id}/votes?limit=8&offset=${offset}`)
      .then((response) =>
        response.ok
          ? response.json()
          : Promise.reject(new Error("Não foi possível carregar os votos.")),
      )
      .then(setVotesPage)
      .catch((exception) => setVotesError(exception.message))
      .finally(() => setVotesLoading(false));
  };
  const applyFinancialFilter = () => {
    if (financialPeriod.mode === "month" && !financialPeriod.month) {
      setFinancialFilterError("Escolha um mês para consultar.");
      return;
    }
    if (financialPeriod.mode === "exact" && !financialPeriod.date) {
      setFinancialFilterError("Escolha uma data para consultar.");
      return;
    }
    if (
      financialPeriod.mode === "range" &&
      (!financialPeriod.dateFrom || !financialPeriod.dateTo)
    ) {
      setFinancialFilterError("Informe as duas datas do intervalo.");
      return;
    }
    if (financialPeriod.mode === "range" && financialPeriod.dateFrom > financialPeriod.dateTo) {
      setFinancialFilterError("A data inicial deve ser anterior à data final.");
      return;
    }
    setFinancialFilterError("");
    setAppliedFinancialPeriod(financialPeriod);
    setFinancialExpensesPage(null);
    loadFinancialExpenses(0, financialPeriod);
  };
  const periodLabel = () => {
    if (appliedFinancialPeriod.mode === "year") {
      return appliedFinancialPeriod.year || String(person?.financial_summary.year ?? "");
    }
    if (appliedFinancialPeriod.mode === "month" && appliedFinancialPeriod.month) {
      return new Date(`${appliedFinancialPeriod.month}-01T12:00:00`).toLocaleDateString("pt-BR", {
        month: "long",
        year: "numeric",
      });
    }
    if (appliedFinancialPeriod.mode === "exact" && appliedFinancialPeriod.date) {
      return formatDate(appliedFinancialPeriod.date);
    }
    if (appliedFinancialPeriod.mode === "range") {
      return `${formatDate(appliedFinancialPeriod.dateFrom) ?? "Início"} a ${formatDate(appliedFinancialPeriod.dateTo) ?? "fim"}`;
    }
    return "período selecionado";
  };
  const financialYears = Array.from(
    new Set([
      ...Array.from({ length: 10 }, (_, index) => String(new Date().getFullYear() - index)),
      String(person?.financial_summary.year ?? ""),
      financialPeriod.year,
    ]),
  )
    .filter(Boolean)
    .sort((left, right) => Number(right) - Number(left));
  const electionLabel =
    person?.election_status?.startsWith("ELEITO") === true ? "Eleito com" : "Votos registrados";

  return (
    <main className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-5xl px-6 py-5">
          <button
            type="button"
            onClick={() => router.back()}
            className="font-bold text-slate-900 hover:text-emerald-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700"
          >
            ← Voltar para representantes
          </button>
        </div>
      </header>
      <section id="conteudo" tabIndex={-1} className="mx-auto max-w-5xl px-6 py-12">
        {error && <div className="rounded-xl bg-red-50 p-5 text-red-800">{error}</div>}
        {!person && !error && <p className="text-slate-500">Carregando perfil…</p>}
        {person && (
          <>
            <div
              className="flex flex-col gap-8 rounded-3xl border p-8 text-white shadow-sm sm:flex-row sm:items-center sm:justify-between"
              style={{
                borderColor: `${partyColor}66`,
                backgroundColor: partyColor,
                backgroundImage:
                  "linear-gradient(112deg, rgba(7, 20, 38, 0.58) 0%, rgba(16, 35, 64, 0.36) 48%, rgba(16, 35, 64, 0.12) 100%)",
              }}
            >
              <div
                className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full text-3xl font-bold"
                style={{
                  backgroundColor: `${partyColor}33`,
                  color: partyAccent,
                }}
              >
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
                  personInitials
                )}
              </div>
              <div className="min-w-0">
                <p className="text-sm uppercase tracking-widest" style={{ color: partyAccent }}>
                  {person.source === "senado"
                    ? "Senado Federal · Senador"
                    : "Câmara dos Deputados · Deputado federal"}
                </p>
                <h1 className="mt-2 text-4xl font-bold">{person.name}</h1>
                <p className="mt-2 text-slate-300">
                  {person.party ?? "Partido não informado"} · {person.state ?? "UF não informada"} ·
                  ID {person.external_id}
                </p>
              </div>
              <PartyMark party={person.party} />
            </div>
            <div className="mt-8 grid gap-5 lg:grid-cols-2">
              <section className="rounded-2xl border bg-white p-6 shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-widest text-emerald-700">
                      Resumo parlamentar
                    </p>
                    <h2 className="mt-2 text-xl font-bold text-slate-950">Dados do mandato</h2>
                  </div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                    {person.is_current ? "Em exercício" : "Registro histórico"}
                  </span>
                </div>
                <dl className="mt-6 grid grid-cols-2 gap-x-4 gap-y-5">
                  <div>
                    <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Cargo
                    </dt>
                    <dd className="mt-1 font-semibold text-slate-900">
                      {person.source === "senado" ? "Senador" : "Deputado federal"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      UF
                    </dt>
                    <dd className="mt-1 font-semibold text-slate-900">
                      {person.state ?? "Não informado"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Partido
                    </dt>
                    <dd className="mt-1 font-semibold text-slate-900">
                      {person.party ?? "Não informado"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Legislatura
                    </dt>
                    <dd className="mt-1 font-semibold text-slate-900">
                      {person.legislature ?? "Não informada"}
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Última coleta
                    </dt>
                    <dd className="mt-1 font-semibold text-slate-900">
                      {new Date(person.collected_at).toLocaleString("pt-BR", {
                        timeZone: "America/Sao_Paulo",
                      })}
                    </dd>
                  </div>
                </dl>
                <div className="mt-6 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">
                  {person.source === "senado" ? (
                    <>Registro do Senado Federal identificado pelo ID {person.external_id}.</>
                  ) : person.birth_date ? (
                    <>
                      Nascimento: <strong>{formatDate(person.birth_date)}</strong>
                      {ageFromBirthDate(person.birth_date) !== null && (
                        <> · {ageFromBirthDate(person.birth_date)} anos</>
                      )}
                      . Dado publicado no perfil oficial identificado pelo ID {person.external_id}.
                    </>
                  ) : (
                    <>
                      Data de nascimento não publicada na fonte oficial consultada. O registro é
                      identificado pelo ID {person.external_id}.
                    </>
                  )}
                  {person.profile_source_url && (
                    <a
                      href={person.profile_source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="ml-2 font-semibold text-emerald-800 hover:underline"
                    >
                      Consultar perfil ↗
                    </a>
                  )}
                </div>
              </section>

              <section className="rounded-2xl border bg-white p-6 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-widest text-emerald-700">
                  Eleição e mandato
                </p>
                <h2 className="mt-2 text-xl font-bold text-slate-950">Como chegou ao cargo</h2>
                <dl className="mt-6 space-y-5">
                  <div>
                    <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {electionLabel}
                    </dt>
                    <dd className="mt-1 text-lg font-bold text-slate-900">
                      {person.election_votes !== null
                        ? `${person.election_votes.toLocaleString("pt-BR")} votos`
                        : "Não associado com segurança"}
                    </dd>
                    {person.election_year !== null && (
                      <p className="mt-1 text-xs text-slate-500">
                        Eleição de {person.election_year}
                      </p>
                    )}
                  </div>
                  <div>
                    <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Exercício parlamentar
                    </dt>
                    <dd className="mt-1 font-semibold text-slate-900">
                      {person.mandate_started_on || person.mandate_ended_on
                        ? `Desde ${formatDate(person.mandate_started_on) ?? "início não informado"} até ${formatDate(person.mandate_ended_on) ?? "em aberto"}`
                        : "Datas individuais indisponíveis na coleta do portal"}
                    </dd>
                  </div>
                </dl>
                {person.source === "senado" ? (
                  <a
                    href={`https://legis.senado.leg.br/dadosabertos/senador/${encodeURIComponent(person.external_id)}/mandatos`}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 inline-block text-sm font-semibold text-emerald-700 hover:underline"
                  >
                    Consultar histórico oficial de mandatos ↗
                  </a>
                ) : (
                  <p className="mt-6 rounded-xl bg-slate-50 p-4 text-xs leading-5 text-slate-600">
                    {person.election_votes !== null
                      ? "Resultado nominal publicado pelo TSE para o primeiro turno de 2022."
                      : "Não foi encontrada correspondência exata e única entre este perfil e o resultado nominal do TSE de 2022. A ausência de valor não significa zero votos."}
                  </p>
                )}
                {person.election_source_url && (
                  <a
                    href={person.election_source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 inline-block text-sm font-semibold text-emerald-700 hover:underline"
                  >
                    Consultar resultado eleitoral ↗
                  </a>
                )}
              </section>

              <section className="rounded-2xl border bg-white p-6 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-widest text-emerald-700">
                  Atuação legislativa
                </p>
                {person.source === "senado" && (
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    Totais dos registros coletados pelo portal, com cobertura parcial de matérias e
                    votos.
                  </p>
                )}
                <div className="mt-5 grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-emerald-50 p-4">
                    <p className="text-2xl font-bold text-emerald-900">
                      {person.authored_propositions_total}
                    </p>
                    <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-emerald-800">
                      Projetos de autoria
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-100 p-4">
                    <p className="text-2xl font-bold text-slate-900">{person.votes_total}</p>
                    <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Votos nominais
                    </p>
                  </div>
                </div>
                {voteBreakdown.length > 0 && (
                  <div className="mt-5 flex flex-wrap gap-2">
                    {voteBreakdown.map(([position, total]) => (
                      <span
                        key={position}
                        className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-700"
                      >
                        {position}: {total}
                      </span>
                    ))}
                  </div>
                )}
                <div className="mt-6 border-t border-slate-200 pt-5">
                  <p className="text-sm font-semibold text-slate-900">Projetos identificados</p>
                  {authoredPropositions.length > 0 ? (
                    <div className="mt-3 space-y-3">
                      {authoredPropositions
                        .slice(0, projectsExpanded ? 5 : 3)
                        .map((proposition) => (
                          <Link
                            key={proposition.id}
                            href={`/proposicoes/${proposition.id}`}
                            className="block rounded-xl border border-slate-200 p-3 transition hover:border-emerald-500 hover:bg-emerald-50"
                          >
                            <span className="text-xs font-bold uppercase tracking-wide text-emerald-700">
                              {proposition.label}
                              {person.source === "senado" && proposition.presented_at
                                ? ` · ${new Date(proposition.presented_at).toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" })}`
                                : ""}
                            </span>
                            <span className="mt-1 block text-sm font-semibold text-slate-900">
                              {proposition.summary}
                            </span>
                          </Link>
                        ))}
                    </div>
                  ) : (
                    <p className="mt-3 text-sm leading-6 text-slate-600">
                      Nenhum projeto de autoria foi identificado na coleta atual.
                    </p>
                  )}
                  {person.authored_propositions_total > 3 && !projectsExpanded && (
                    <button
                      type="button"
                      onClick={expandProjects}
                      className="mt-4 text-sm font-semibold text-emerald-800 hover:underline"
                    >
                      Ver todos os projetos
                    </button>
                  )}
                  {projectsExpanded && projectsPage && projectsPage.total > projectsPage.limit && (
                    <div className="mt-4 flex items-center justify-between gap-2">
                      <button
                        type="button"
                        disabled={projectsPage.offset === 0 || projectsLoading}
                        onClick={() => loadProjects(projectsPage.offset - projectsPage.limit)}
                        className="text-xs font-semibold text-slate-700 disabled:opacity-40"
                      >
                        ← Anteriores
                      </button>
                      <span className="text-xs text-slate-500">
                        {projectsPage.offset + 1}–
                        {Math.min(projectsPage.offset + projectsPage.limit, projectsPage.total)} de{" "}
                        {projectsPage.total}
                      </span>
                      <button
                        type="button"
                        disabled={
                          projectsPage.offset + projectsPage.limit >= projectsPage.total ||
                          projectsLoading
                        }
                        onClick={() => loadProjects(projectsPage.offset + projectsPage.limit)}
                        className="text-xs font-semibold text-slate-700 disabled:opacity-40"
                      >
                        Próximos →
                      </button>
                    </div>
                  )}
                  {projectsError && (
                    <p className="mt-3 text-sm font-semibold text-rose-700" role="alert">
                      {projectsError}
                    </p>
                  )}
                </div>
              </section>

              {person.source === "senado" ? (
                <section className="rounded-2xl border bg-white p-6 shadow-sm">
                  <h2 className="text-xl font-bold text-slate-950">Transparência do Senado</h2>
                  <p className="mt-3 text-sm leading-6 text-slate-600">
                    Consulte remuneração, cotas e informações de gabinete no portal oficial.
                  </p>
                  <a
                    href="https://www25.senado.leg.br/web/transparencia/sen"
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 inline-block text-sm font-semibold text-emerald-700 hover:underline"
                  >
                    Abrir transparência do Senado ↗
                  </a>
                </section>
              ) : (
                <section className="rounded-2xl border bg-white p-6 shadow-sm">
                  <p className="text-sm font-semibold uppercase tracking-widest text-emerald-700">
                    Transparência financeira
                  </p>
                  <p className="mt-2 text-xl font-bold text-slate-950">Informações financeiras</p>
                  <p className="mt-3 text-sm leading-6 text-slate-600">
                    Separamos o que já foi coletado para este parlamentar das referências gerais
                    publicadas pela fonte oficial.
                  </p>
                  <dl className="mt-6 grid gap-4 sm:grid-cols-2">
                    <div className="rounded-xl bg-emerald-50 p-4">
                      <dt className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                        Remuneração mensal publicada
                      </dt>
                      <dd className="mt-1 text-lg font-bold text-emerald-950">
                        {person.financial_summary.remuneration_fixed !== null
                          ? formatCurrency(person.financial_summary.remuneration_fixed)
                          : formatCurrency(person.financial_summary.subsidy_reference)}
                      </dd>
                      <p className="mt-2 text-xs leading-5 text-emerald-900/75">
                        {person.financial_summary.remuneration_fixed !== null
                          ? `Valor fixo bruto publicado na folha de ${String(person.financial_summary.remuneration_month).padStart(2, "0")}/${person.financial_summary.remuneration_year}.`
                          : (person.financial_summary.subsidy_note ?? "Referência não coletada.")}
                      </p>
                      {person.financial_summary.remuneration_net !== null && (
                        <p className="mt-2 text-xs font-semibold text-emerald-950">
                          Após descontos obrigatórios:{" "}
                          {formatCurrency(person.financial_summary.remuneration_net)}
                        </p>
                      )}
                      {person.financial_summary.remuneration_collected_at && (
                        <p className="mt-2 text-[11px] leading-4 text-emerald-900/70">
                          Câmara dos Deputados · coletado em{" "}
                          {formatCollectedAt(person.financial_summary.remuneration_collected_at)}
                        </p>
                      )}
                      {(person.financial_summary.remuneration_source_url ||
                        person.financial_summary.subsidy_source_url) && (
                        <a
                          href={
                            person.financial_summary.remuneration_source_url ??
                            person.financial_summary.subsidy_source_url ??
                            "#"
                          }
                          target="_blank"
                          rel="noreferrer"
                          className="mt-3 inline-flex text-xs font-semibold text-emerald-800 hover:underline"
                        >
                          Consultar folha oficial ↗
                        </a>
                      )}
                    </div>
                    <div className="rounded-xl bg-slate-100 p-4">
                      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                        Cota parlamentar (CEAP)
                      </dt>
                      <dd className="mt-1 text-lg font-bold text-slate-950">
                        {person.financial_summary.available
                          ? formatCurrency(person.financial_summary.net_total)
                          : person.is_current
                            ? "Não coletada"
                            : "Sem despesa coletada"}
                      </dd>
                      <p className="mt-2 text-xs leading-5 text-slate-600">
                        {person.financial_summary.available
                          ? `${person.financial_summary.expense_count.toLocaleString("pt-BR")} documentos${person.financial_summary.year ? ` · ${person.financial_summary.year_from && person.financial_summary.year_from !== person.financial_summary.year ? `${person.financial_summary.year_from}–${person.financial_summary.year}` : person.financial_summary.year}` : ""}`
                          : person.is_current
                            ? "Nenhuma despesa oficial encontrada na coleta atual."
                            : "Nenhuma despesa foi associada nos recortes disponíveis."}
                      </p>
                      {person.financial_summary.expense_collected_at && (
                        <p className="mt-2 text-[11px] leading-4 text-slate-500">
                          Câmara dos Deputados · coletado em{" "}
                          {formatCollectedAt(person.financial_summary.expense_collected_at)}
                        </p>
                      )}
                    </div>
                  </dl>
                  {person.financial_summary.available && (
                    <p className="mt-4 text-xs text-slate-500">
                      Glosas registradas: {formatCurrency(person.financial_summary.glossed_total)}
                    </p>
                  )}
                  {person.financial_summary.source_url && (
                    <button
                      type="button"
                      onClick={openFinancialSource}
                      className="mt-5 inline-flex items-center gap-2 text-left text-sm font-semibold text-emerald-700 hover:text-emerald-900 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2"
                    >
                      Ver detalhes das despesas oficiais <span aria-hidden="true">↗</span>
                    </button>
                  )}
                  <dl className="mt-6 space-y-3 border-t border-slate-100 pt-5">
                    <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-3">
                      <dt className="text-sm text-slate-700">Assessores e equipe</dt>
                      <dd className="text-right text-xs font-semibold text-slate-500">
                        {person.financial_summary.staff_count !== null
                          ? `${person.financial_summary.staff_count.toLocaleString("pt-BR")} em exercício`
                          : person.is_current
                            ? "Não coletado"
                            : "Não aplicável ao registro histórico"}
                      </dd>
                    </div>
                    {person.financial_summary.staff_collected_at && (
                      <p className="text-xs leading-5 text-slate-500">
                        Competência {String(person.financial_summary.staff_month).padStart(2, "0")}/
                        {person.financial_summary.staff_year} · Câmara dos Deputados · coletado em{" "}
                        {formatCollectedAt(person.financial_summary.staff_collected_at)}
                      </p>
                    )}
                    {person.financial_summary.staff_source_url && (
                      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
                        <button
                          type="button"
                          onClick={openStaff}
                          className="inline-flex text-xs font-semibold text-emerald-800 hover:underline"
                        >
                          Ver equipe nominal
                        </button>
                        <a
                          href={person.financial_summary.staff_source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex text-xs font-semibold text-emerald-800 hover:underline"
                        >
                          Consultar equipe na Câmara ↗
                        </a>
                        {person.financial_summary.staff_count !== null && (
                          <a
                            href={`${API_URL}/parliamentarians/${params.id}/staff.pdf`}
                            className="inline-flex text-xs font-semibold text-slate-700 hover:text-emerald-800 hover:underline"
                          >
                            Baixar relatório PDF ↓
                          </a>
                        )}
                      </div>
                    )}
                  </dl>
                </section>
              )}
              <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-widest text-emerald-700">
                    Emendas parlamentares
                  </p>
                  <h2 className="mt-2 text-xl font-bold text-slate-950">
                    Consulte os registros oficiais
                  </h2>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                    As emendas são registradas e atualizadas no Portal da Transparência. Para
                    consultar os dados mais recentes, abra a fonte oficial e filtre pelo nome do
                    parlamentar.
                  </p>
                </div>
                <div className="mt-6 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                      O que consultar
                    </p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">
                      Autor, ano, destino e situação da emenda.
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Fonte responsável
                    </p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">
                      Portal da Transparência do Governo Federal.
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Como encontrar
                    </p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">
                      Use o filtro de autor com o nome deste parlamentar.
                    </p>
                  </div>
                </div>
                {person.financial_summary.amendment_count !== null && (
                  <div className="mt-5 flex flex-col gap-3 rounded-xl border border-emerald-100 bg-emerald-50/60 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-emerald-950">
                        Arquivo deste parlamentar
                      </p>
                      <p className="mt-1 text-xs leading-5 text-emerald-900/75">
                        CSV gerado na hora com as {person.financial_summary.amendment_count} emendas
                        coletadas em {person.financial_summary.amendment_year}.
                      </p>
                      {person.financial_summary.amendment_collected_at && (
                        <p className="mt-1 text-[11px] leading-4 text-emerald-900/70">
                          Portal da Transparência (CGU) · coleta em{" "}
                          {formatCollectedAt(person.financial_summary.amendment_collected_at)}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      <a
                        href={`${API_URL}/parliamentarians/${params.id}/amendments.pdf?year=${person.financial_summary.amendment_year}`}
                        className="rounded-lg bg-emerald-800 px-3 py-2 text-sm font-semibold text-white transition hover:bg-emerald-900"
                      >
                        Baixar relatório PDF ↓
                      </a>
                      <a
                        href={`${API_URL}/parliamentarians/${params.id}/amendments.csv?year=${person.financial_summary.amendment_year}`}
                        className="text-sm font-semibold text-emerald-900 hover:underline"
                      >
                        CSV detalhado ↓
                      </a>
                    </div>
                  </div>
                )}
                <div className="mt-5 flex flex-col gap-3 border-t border-slate-200 pt-4 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-xs leading-5 text-slate-600">
                    A consulta oficial pode ser atualizada pela fonte depois da coleta do nosso
                    site.
                  </p>
                  <a
                    href={
                      person.financial_summary.amendment_source_url ??
                      "https://portaldatransparencia.gov.br/emendas/consulta"
                    }
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 text-sm font-semibold text-emerald-800 hover:underline"
                  >
                    Abrir consulta oficial de emendas ↗
                  </a>
                </div>
              </section>
            </div>
            <section className="mt-6 rounded-2xl border bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-widest text-emerald-700">
                    Registro de votos
                  </p>
                  <h2 className="mt-2 text-xl font-bold text-slate-950">
                    Votações nominais recentes
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    {person.source === "senado"
                      ? "Cada coleta importa até as 50 votações nominais mais recentes do ano corrente. Os registros de coletas anteriores continuam disponíveis."
                      : "Mostramos somente votações individuais publicadas pela fonte oficial."}
                  </p>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                  {person.votes_total.toLocaleString("pt-BR")} registros no total
                </span>
              </div>
              {voteRecords.length > 0 ? (
                <div className="mt-6 divide-y divide-slate-100 rounded-xl border border-slate-200">
                  {voteRecords.map((vote) => {
                    const normalizedPosition = vote.position.toLowerCase();
                    const isPositive = normalizedPosition === "sim";
                    const isNegative = normalizedPosition === "não" || normalizedPosition === "nao";
                    const positionClass = isPositive
                      ? "bg-emerald-50 text-emerald-800"
                      : isNegative
                        ? "bg-rose-50 text-rose-800"
                        : "bg-slate-100 text-slate-700";
                    return (
                      <article
                        key={`${vote.voting_id}-${vote.position}`}
                        className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="min-w-0">
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            {vote.occurred_on ? formatDate(vote.occurred_on) : "Data não informada"}
                          </p>
                          <p className="mt-1 line-clamp-2 font-semibold text-slate-900">
                            {vote.object_description ||
                              vote.description ||
                              "Votação sem descrição publicada"}
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            {vote.party_at_vote ??
                              (person.source === "senado" ? null : person.party) ??
                              "Partido à época não informado"}
                            {vote.state_at_vote ? ` · ${vote.state_at_vote}` : ""}
                          </p>
                        </div>
                        <div className="flex shrink-0 items-center gap-3">
                          <span
                            className={`rounded-full px-3 py-1 text-xs font-bold ${positionClass}`}
                          >
                            {vote.position}
                          </span>
                          <Link
                            href={`/votacoes/${vote.voting_id}`}
                            className="text-xs font-semibold text-slate-700 hover:text-emerald-700 hover:underline"
                          >
                            Ver votação
                          </Link>
                          <a
                            href={vote.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs font-semibold text-emerald-700 hover:underline"
                          >
                            Fonte ↗
                          </a>
                        </div>
                      </article>
                    );
                  })}
                </div>
              ) : (
                <div className="mt-6 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">
                  Nenhum voto nominal individual foi encontrado nos registros coletados para este
                  parlamentar.
                </div>
              )}
              {person.votes_total > 8 && (
                <div className="mt-4 flex items-center justify-between gap-3">
                  <button
                    type="button"
                    disabled={!votesPage || votesPage.offset === 0 || votesLoading}
                    onClick={() => votesPage && loadVotes(votesPage.offset - votesPage.limit)}
                    className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-40"
                  >
                    ← Votos anteriores
                  </button>
                  <span className="text-xs text-slate-500">
                    {votesPage
                      ? `${votesPage.offset + 1}–${Math.min(votesPage.offset + votesPage.limit, votesPage.total)} de ${votesPage.total}`
                      : `1–${Math.min(8, person.votes_total)} de ${person.votes_total}`}
                  </span>
                  <button
                    type="button"
                    disabled={
                      votesLoading ||
                      (votesPage
                        ? votesPage.offset + votesPage.limit >= votesPage.total
                        : person.votes_total <= 8)
                    }
                    onClick={() => loadVotes(votesPage ? votesPage.offset + votesPage.limit : 8)}
                    className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-40"
                  >
                    Próximos votos →
                  </button>
                </div>
              )}
              {votesError && (
                <p className="mt-3 text-sm font-semibold text-rose-700" role="alert">
                  {votesError}
                </p>
              )}
            </section>
            <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-widest text-emerald-700">
                    Fonte e mandato
                  </p>
                  <h2 className="mt-1 text-lg font-bold text-slate-950">
                    Dados do registro consultado
                  </h2>
                </div>
                <a
                  className="text-sm font-semibold text-emerald-700 hover:underline"
                  href={person.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Consultar registro oficial ↗
                </a>
              </div>
              <div className="mt-5 grid gap-4 border-t border-slate-100 pt-4 sm:grid-cols-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {person.source === "senado" ? "Legislaturas observadas" : "Mandato observado"}
                  </p>
                  <div className="mt-2 space-y-1">
                    {person.mandates.length === 0 && (
                      <p className="text-sm text-slate-600">Nenhuma legislatura coletada.</p>
                    )}
                    {person.mandates.map((mandate) => (
                      <div key={mandate.legislature}>
                        <p className="text-sm font-semibold text-slate-900">
                          Legislatura {mandate.legislature}
                        </p>
                        <p className="text-sm text-slate-600">
                          {mandate.party ?? "Partido não informado"} · {mandate.state}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Fonte responsável
                  </p>
                  <p className="mt-2 text-sm font-semibold text-slate-900">
                    {person.source === "senado" ? "Senado Federal" : "Câmara dos Deputados"}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Última coleta
                  </p>
                  <p className="mt-2 text-sm font-semibold text-slate-900">
                    {new Date(person.collected_at).toLocaleString("pt-BR")}
                  </p>
                </div>
              </div>
            </section>
            {showStaff && (
              <div
                className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 px-3 py-4 backdrop-blur-sm"
                role="presentation"
                onMouseDown={() => setShowStaff(false)}
              >
                <div
                  className="flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-3xl bg-white p-5 shadow-2xl ring-1 ring-slate-900/10"
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="staff-title"
                  onMouseDown={(event) => event.stopPropagation()}
                >
                  <div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                        Gabinete parlamentar
                      </p>
                      <h2 id="staff-title" className="mt-1 text-2xl font-bold text-slate-950">
                        Equipe de {person.name}
                      </h2>
                      {staffPage?.year && staffPage.month && (
                        <p className="mt-1 text-sm text-slate-600">
                          Competência {String(staffPage.month).padStart(2, "0")}/{staffPage.year} ·{" "}
                          {staffPage.total.toLocaleString("pt-BR")} pessoas publicadas
                        </p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowStaff(false)}
                      aria-label="Fechar equipe nominal"
                      className="rounded-full px-2 py-1 text-2xl leading-none text-slate-500 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
                    >
                      ×
                    </button>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-slate-600">
                    Servidores em exercício na categoria Secretário Parlamentar, conforme a
                    publicação oficial da Câmara. Valores ausentes não são apresentados como zero.
                  </p>
                  {staffPage?.collected_at && (
                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      Fonte: Câmara dos Deputados · coletado em{" "}
                      {formatCollectedAt(staffPage.collected_at)}
                      {staffPage.source_url && (
                        <>
                          {" · "}
                          <a
                            href={staffPage.source_url}
                            target="_blank"
                            rel="noopener noreferrer nofollow"
                            className="font-semibold text-emerald-800 hover:underline"
                          >
                            consulta original ↗
                          </a>
                        </>
                      )}
                    </p>
                  )}
                  {staffError && (
                    <p
                      className="mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-800"
                      role="alert"
                    >
                      {staffError}
                    </p>
                  )}
                  <div className="mt-4 min-h-40 flex-1 overflow-y-auto rounded-2xl border border-slate-200">
                    {staffLoading && !staffPage && (
                      <p className="p-5 text-sm text-slate-600">Carregando equipe…</p>
                    )}
                    {!staffLoading && staffPage?.items.length === 0 && (
                      <p className="p-5 text-sm text-slate-600">
                        A equipe nominal desta competência ainda não foi coletada.
                      </p>
                    )}
                    {staffPage?.items.map((member) => (
                      <article
                        key={member.id}
                        className="border-b border-slate-200 p-4 last:border-b-0"
                      >
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <h3 className="font-bold text-slate-950">{member.name}</h3>
                            <p className="mt-1 text-sm text-slate-600">
                              {member.job_title ?? member.category ?? "Cargo não informado"}
                              {member.level ? ` · Nível ${member.level}` : ""}
                            </p>
                            {member.area_of_work && (
                              <p className="mt-1 text-xs text-slate-500">{member.area_of_work}</p>
                            )}
                            <p className="mt-1 text-[11px] text-slate-400">
                              Referência oficial: {member.external_id}
                            </p>
                          </div>
                          <div className="sm:text-right">
                            <p className="text-xs uppercase tracking-wide text-slate-500">
                              Remuneração líquida
                            </p>
                            <p className="mt-1 font-bold text-slate-900">
                              {formatCurrency(member.net_amount)}
                            </p>
                            {member.source_remuneration_url && (
                              <a
                                href={member.source_remuneration_url}
                                target="_blank"
                                rel="noreferrer"
                                className="mt-1 inline-flex text-xs font-semibold text-emerald-800 hover:underline"
                              >
                                Fonte da remuneração ↗
                              </a>
                            )}
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                  {staffPage && staffPage.total > staffPage.limit && (
                    <div className="mt-4 flex items-center justify-between gap-3">
                      <button
                        type="button"
                        disabled={staffPage.offset === 0 || staffLoading}
                        onClick={() => loadStaff(staffPage.offset - staffPage.limit)}
                        className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold disabled:opacity-40"
                      >
                        ← Anteriores
                      </button>
                      <span className="text-xs text-slate-500">
                        {staffPage.offset + 1}–
                        {Math.min(staffPage.offset + staffPage.limit, staffPage.total)} de{" "}
                        {staffPage.total}
                      </span>
                      <button
                        type="button"
                        disabled={
                          staffPage.offset + staffPage.limit >= staffPage.total || staffLoading
                        }
                        onClick={() => loadStaff(staffPage.offset + staffPage.limit)}
                        className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold disabled:opacity-40"
                      >
                        Próximas →
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
            {showFinancialSource && person.financial_summary.available && (
              <div
                className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 px-2 py-2 backdrop-blur-sm sm:px-4 sm:py-3"
                role="presentation"
                onMouseDown={() => setShowFinancialSource(false)}
              >
                <div
                  className="flex h-[97vh] max-h-[calc(100vh-0.75rem)] w-full max-w-6xl flex-col overflow-hidden rounded-3xl bg-white p-4 shadow-2xl ring-1 ring-slate-900/10 sm:p-5"
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="financial-source-title"
                  onMouseDown={(event) => event.stopPropagation()}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                        Transparência financeira
                      </p>
                      <h2
                        id="financial-source-title"
                        className="mt-1 text-xl font-bold text-slate-950 sm:text-2xl"
                      >
                        Despesas de {person.name}
                      </h2>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowFinancialSource(false)}
                      aria-label="Fechar detalhes da fonte"
                      className="rounded-full px-2 py-1 text-2xl leading-none text-slate-500 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
                    >
                      ×
                    </button>
                  </div>
                  <div className="mt-3 flex items-center gap-3 rounded-2xl border border-emerald-100 bg-emerald-50/70 px-3 py-2">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full border border-emerald-200 bg-white text-base font-bold text-emerald-800">
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
                        personInitials
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-800">
                        Parlamentar consultado
                      </p>
                      <p className="truncate text-sm font-bold text-slate-950">{person.name}</p>
                      <p className="text-xs text-slate-600">
                        {person.source === "senado" ? "Senador" : "Deputado federal"} ·{" "}
                        {person.party ?? "Partido não informado"} ·{" "}
                        {person.state ?? "UF não informada"} · ID {person.external_id}
                      </p>
                    </div>
                  </div>
                  <p className="mt-3 text-xs leading-5 text-slate-600 sm:text-sm">
                    Despesas registradas na Cota para o Exercício da Atividade Parlamentar (CEAP).
                    Abaixo estão os documentos já normalizados para leitura.
                  </p>
                  <p className="mt-2 rounded-xl bg-slate-50 p-2.5 text-[11px] leading-4 text-slate-600 sm:px-3">
                    A consulta do comprovante ocorre no portal oficial da Câmara. A nota pode conter
                    dados pessoais publicados pela própria fonte.
                  </p>
                  <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-50/70 p-3 sm:flex sm:flex-wrap sm:items-end sm:gap-2">
                    <div className="flex flex-col gap-2 sm:contents">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
                          Filtrar período
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          Escolha como deseja consultar os documentos da CEAP.
                        </p>
                      </div>
                      <div className="sm:min-w-52">
                        <FilterSelect
                          id="financial-period-mode"
                          label="Tipo de período"
                          value={financialPeriodLabels[financialPeriod.mode]}
                          placeholder="Ano inteiro"
                          options={Object.values(financialPeriodLabels).filter(
                            (label) => label !== financialPeriodLabels[financialPeriod.mode],
                          )}
                          onChange={(label) => {
                            const mode = Object.entries(financialPeriodLabels).find(
                              ([, value]) => value === label,
                            )?.[0] as FinancialPeriodMode | undefined;
                            if (mode) {
                              setFinancialFilterError("");
                              setFinancialPeriod((current) => ({ ...current, mode }));
                            }
                          }}
                        />
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap items-end gap-2 sm:contents">
                      {financialPeriod.mode === "year" && (
                        <div className="w-40">
                          <FilterSelect
                            id="financial-period-year"
                            label="Ano"
                            value={financialPeriod.year}
                            placeholder={String(person?.financial_summary.year ?? "Ano")}
                            options={financialYears.filter((year) => year !== financialPeriod.year)}
                            onChange={(year) =>
                              setFinancialPeriod((current) => ({ ...current, year }))
                            }
                          />
                        </div>
                      )}
                      {financialPeriod.mode === "month" && (
                        <label className="text-xs font-semibold text-slate-600">
                          Mês
                          <input
                            type="month"
                            value={financialPeriod.month}
                            onChange={(event) =>
                              setFinancialPeriod((current) => ({
                                ...current,
                                month: event.target.value,
                              }))
                            }
                            onInput={(event) =>
                              setFinancialPeriod((current) => ({
                                ...current,
                                month: event.currentTarget.value,
                              }))
                            }
                            className="mt-1 block rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-normal text-slate-800 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                          />
                        </label>
                      )}
                      {financialPeriod.mode === "exact" && (
                        <label className="text-xs font-semibold text-slate-600">
                          Data
                          <input
                            type="date"
                            value={financialPeriod.date}
                            onChange={(event) =>
                              setFinancialPeriod((current) => ({
                                ...current,
                                date: event.target.value,
                              }))
                            }
                            onInput={(event) =>
                              setFinancialPeriod((current) => ({
                                ...current,
                                date: event.currentTarget.value,
                              }))
                            }
                            className="mt-1 block rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-normal text-slate-800 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                          />
                        </label>
                      )}
                      {financialPeriod.mode === "range" && (
                        <>
                          <label className="text-xs font-semibold text-slate-600">
                            De
                            <input
                              type="date"
                              value={financialPeriod.dateFrom}
                              onChange={(event) =>
                                setFinancialPeriod((current) => ({
                                  ...current,
                                  dateFrom: event.target.value,
                                }))
                              }
                              onInput={(event) =>
                                setFinancialPeriod((current) => ({
                                  ...current,
                                  dateFrom: event.currentTarget.value,
                                }))
                              }
                              className="mt-1 block rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-normal text-slate-800 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                            />
                          </label>
                          <label className="text-xs font-semibold text-slate-600">
                            Até
                            <input
                              type="date"
                              value={financialPeriod.dateTo}
                              onChange={(event) =>
                                setFinancialPeriod((current) => ({
                                  ...current,
                                  dateTo: event.target.value,
                                }))
                              }
                              onInput={(event) =>
                                setFinancialPeriod((current) => ({
                                  ...current,
                                  dateTo: event.currentTarget.value,
                                }))
                              }
                              className="mt-1 block rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-normal text-slate-800 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                            />
                          </label>
                        </>
                      )}
                      <button
                        type="button"
                        onClick={applyFinancialFilter}
                        disabled={financialExpensesLoading}
                        className="min-h-11 self-end rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-wait disabled:opacity-60"
                      >
                        Aplicar filtro
                      </button>
                    </div>
                    {financialFilterError && (
                      <p
                        className="mt-3 text-xs font-semibold text-rose-700 sm:basis-full"
                        role="alert"
                      >
                        {financialFilterError}
                      </p>
                    )}
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {financialExpensesPage?.total.toLocaleString("pt-BR") ?? "—"} documentos ·{" "}
                      {periodLabel()}
                    </p>
                    {financialExpensesPage && (
                      <p className="text-xs text-slate-500">
                        Página{" "}
                        {Math.floor(financialExpensesPage.offset / financialExpensesPage.limit) + 1}
                      </p>
                    )}
                  </div>
                  {financialExpensesPage?.items[0] && (
                    <p className="mt-1 text-[11px] leading-4 text-slate-500">
                      Fonte: Câmara dos Deputados · coletado em{" "}
                      {formatCollectedAt(financialExpensesPage.items[0].collected_at)} ·{" "}
                      <a
                        href={financialExpensesPage.items[0].source_url}
                        target="_blank"
                        rel="noopener noreferrer nofollow"
                        className="font-semibold text-emerald-800 hover:underline"
                      >
                        arquivo anual original ↗
                      </a>
                    </p>
                  )}
                  {financialExpensesError && (
                    <p className="mt-2 rounded-xl bg-rose-50 p-3 text-sm text-rose-800">
                      {financialExpensesError}
                    </p>
                  )}
                  <div className="relative mt-2 min-h-0 flex-1 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/40">
                    {financialExpensesPage &&
                      financialExpensesPage.total > financialExpensesPage.items.length && (
                        <div className="pointer-events-none absolute right-3 top-3 z-10 rounded-full border border-slate-200 bg-white/95 px-3 py-1.5 text-[11px] font-semibold text-slate-500 shadow-sm">
                          ↓ Role para ver mais
                        </div>
                      )}
                    {!financialExpensesError && financialExpensesPage && (
                      <div
                        className={`h-full min-h-0 grid auto-rows-max gap-2 overflow-y-auto p-2 pr-1 transition-opacity duration-200 sm:gap-3 sm:p-3 sm:grid-cols-2 ${financialExpensesLoading ? "opacity-55" : "opacity-100"}`}
                        aria-busy={financialExpensesLoading}
                      >
                        {financialExpensesPage.items.map((expense) => (
                          <article
                            key={expense.id}
                            className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
                          >
                            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                              <div className="min-w-0">
                                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                                  {expense.occurred_on
                                    ? formatDate(expense.occurred_on)
                                    : "Data não informada"}
                                </p>
                                <h3 className="mt-1 text-sm font-semibold text-slate-950">
                                  {expense.category}
                                </h3>
                                <p className="mt-1 text-xs leading-5 text-slate-600">
                                  {expense.category_detail || "Detalhamento não informado"}
                                </p>
                                <p className="mt-1 text-xs text-slate-500">
                                  {expense.supplier_name || "Fornecedor não informado"}
                                  {expense.document_number
                                    ? ` · Doc. ${expense.document_number}`
                                    : ""}
                                </p>
                                <p className="mt-1 text-[11px] text-slate-400">
                                  Referência oficial: {expense.external_id} · exercício{" "}
                                  {expense.year}
                                </p>
                              </div>
                              <div className="shrink-0 sm:text-right">
                                <p className="text-xs uppercase tracking-wide text-slate-500">
                                  Líquido
                                </p>
                                <p className="text-sm font-bold text-slate-950">
                                  {formatCurrency(expense.amount_net)}
                                </p>
                                {expense.amount_glossed !== null &&
                                  Number(expense.amount_glossed) > 0 && (
                                    <p className="mt-1 text-xs text-rose-700">
                                      Glosa: {formatCurrency(expense.amount_glossed)}
                                    </p>
                                  )}
                              </div>
                            </div>
                            {expense.source_document_url && (
                              <a
                                href={expense.source_document_url}
                                target="_blank"
                                rel="noopener noreferrer nofollow"
                                className="mt-2 inline-block text-xs font-semibold text-emerald-700 hover:underline"
                              >
                                Ver documento oficial ↗
                              </a>
                            )}
                          </article>
                        ))}
                      </div>
                    )}
                    {financialExpensesLoading && (
                      <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-white/65 backdrop-blur-[1px]">
                        <p className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 shadow-sm">
                          Atualizando despesas…
                        </p>
                      </div>
                    )}
                    {!financialExpensesLoading &&
                      !financialExpensesError &&
                      !financialExpensesPage && (
                        <div className="flex min-h-32 items-center justify-center rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
                          Nenhuma despesa coletada foi encontrada para este período. Isso não prova
                          gasto zero.
                        </div>
                      )}
                  </div>
                  {financialExpensesPage &&
                    financialExpensesPage.total > financialExpensesPage.limit && (
                      <div className="mt-1 flex items-center justify-between gap-3 border-t border-slate-100 pt-1">
                        <button
                          type="button"
                          disabled={financialExpensesPage.offset === 0 || financialExpensesLoading}
                          onClick={() =>
                            loadFinancialExpenses(
                              financialExpensesPage.offset - financialExpensesPage.limit,
                            )
                          }
                          className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          ← Anteriores
                        </button>
                        <span className="text-xs text-slate-500">
                          {financialExpensesPage.offset + 1}–
                          {Math.min(
                            financialExpensesPage.offset + financialExpensesPage.limit,
                            financialExpensesPage.total,
                          )}
                        </span>
                        <button
                          type="button"
                          disabled={
                            financialExpensesPage.offset + financialExpensesPage.limit >=
                              financialExpensesPage.total || financialExpensesLoading
                          }
                          onClick={() =>
                            loadFinancialExpenses(
                              financialExpensesPage.offset + financialExpensesPage.limit,
                            )
                          }
                          className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          Próximas →
                        </button>
                      </div>
                    )}
                  <div className="mt-2 flex flex-col-reverse gap-2 sm:flex-row sm:items-center">
                    <p className="flex-1 rounded-xl bg-amber-50 px-3 py-2 text-[11px] leading-4 text-amber-900">
                      CEAP é despesa documental da atividade parlamentar. Este número não é salário,
                      não representa emendas e não corresponde ao custo total do mandato. O
                      comprovante abre na Câmara e pode conter dados pessoais publicados pela fonte;
                      compartilhe somente quando necessário.
                    </p>
                    <button
                      type="button"
                      onClick={() => setShowFinancialSource(false)}
                      className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
                    >
                      Fechar
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}
