export type Parliamentarian = {
  id: string;
  external_id: string;
  name: string;
  photo_url: string | null;
  state: string | null;
  party: string | null;
  legislature: string | null;
  source_url: string;
  source: "camara" | "senado";
  collected_at: string;
  is_current: boolean;
};
export type ParliamentarianPage = {
  items: Parliamentarian[];
  total: number;
  limit: number;
  offset: number;
};
export type Proposition = {
  id: string;
  external_id: string;
  kind: string;
  number: number | null;
  year: number | null;
  summary: string;
  presented_at: string | null;
  source_url: string;
  source: "camara" | "senado";
  collected_at: string;
};
export type Voting = {
  id: string;
  external_id: string;
  occurred_on: string | null;
  description: string;
  object_description: string | null;
  approved: boolean | null;
  mode: string | null;
  source_url: string;
  source: "camara" | "senado";
  collected_at: string;
};
export type PropositionPage = {
  items: Proposition[];
  total: number;
  limit: number;
  offset: number;
  facets: { years: number[]; kinds: string[] };
};
export type VotingPage = {
  items: Voting[];
  total: number;
  limit: number;
  offset: number;
  facets: { years: number[]; modes: string[] };
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function fetchParliamentarians(
  params: {
    search?: string;
    state?: string;
    party?: string;
    source?: "camara" | "senado";
    status?: "current" | "historical" | "all";
    limit?: number;
    offset?: number;
  } = {},
) {
  const query = new URLSearchParams({
    limit: String(params.limit ?? 24),
    offset: String(params.offset ?? 0),
  });
  if (params.search) query.set("search", params.search);
  if (params.state) query.set("state", params.state);
  if (params.party) query.set("party", params.party);
  if (params.source) query.set("source", params.source);
  if (params.status) query.set("status", params.status);
  const response = await fetch(`${API_URL}/parliamentarians?${query}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Não foi possível carregar os parlamentares.");
  return response.json() as Promise<ParliamentarianPage>;
}

export async function fetchParliamentarianParties(source: "camara" | "senado" = "camara") {
  const response = await fetch(`${API_URL}/parliamentarians/parties?source=${source}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Não foi possível carregar os partidos.");
  return response.json() as Promise<string[]>;
}

export async function fetchPropositions(source: "camara" | "senado" = "camara") {
  const response = await fetch(`${API_URL}/propositions?limit=6&source=${source}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Não foi possível carregar os projetos.");
  return response.json() as Promise<Proposition[]>;
}

export async function fetchVotings(source: "camara" | "senado" = "camara") {
  const response = await fetch(`${API_URL}/votings?limit=6&source=${source}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Não foi possível carregar as votações.");
  return response.json() as Promise<Voting[]>;
}

export async function searchPropositions(params: {
  source: "camara" | "senado";
  q?: string;
  year?: string;
  kind?: string;
  order?: "newest" | "oldest" | "number_asc" | "number_desc";
  limit?: number;
  offset?: number;
}) {
  const query = new URLSearchParams({
    source: params.source,
    order: params.order ?? "newest",
    limit: String(params.limit ?? 12),
    offset: String(params.offset ?? 0),
  });
  if (params.q) query.set("q", params.q);
  if (params.year) query.set("year", params.year);
  if (params.kind) query.set("kind", params.kind);
  const response = await fetch(`${API_URL}/propositions/search?${query}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Não foi possível consultar os projetos agora.");
  return response.json() as Promise<PropositionPage>;
}

export async function searchVotings(params: {
  source: "camara" | "senado";
  q?: string;
  year?: string;
  result?: "approved" | "rejected" | "unknown" | "";
  mode?: "nominal" | "unknown" | "";
  order?: "newest" | "oldest";
  limit?: number;
  offset?: number;
}) {
  const query = new URLSearchParams({
    source: params.source,
    order: params.order ?? "newest",
    limit: String(params.limit ?? 12),
    offset: String(params.offset ?? 0),
  });
  if (params.q) query.set("q", params.q);
  if (params.year) query.set("year", params.year);
  if (params.result) query.set("result", params.result);
  if (params.mode) query.set("mode", params.mode);
  const response = await fetch(`${API_URL}/votings/search?${query}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Não foi possível consultar as votações agora.");
  return response.json() as Promise<VotingPage>;
}
