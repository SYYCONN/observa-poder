"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { FilterSelect } from "@/components/filter-select";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
type RunStatus = "generating" | "published" | "rejected" | "failed";
type Run = {
  id: string;
  proposition_id: string;
  label: string;
  summary: string;
  status: RunStatus;
  provider: string;
  generation_model: string;
  verification_model: string;
  prompt_version: string;
  error_code: string | null;
  deterministic_checks: { passed?: boolean } | null;
  ai_verification: { approved?: boolean } | null;
  started_at: string;
  finished_at: string | null;
};
type RunPage = {
  items: Run[];
  total: number;
  counts: Record<RunStatus, number>;
};

const labels: Record<RunStatus, string> = {
  generating: "Processando",
  published: "Publicado",
  rejected: "Não publicado",
  failed: "Falha temporária",
};
const colors: Record<RunStatus, string> = {
  generating: "bg-blue-100 text-blue-900",
  published: "bg-emerald-100 text-emerald-900",
  rejected: "bg-amber-100 text-amber-950",
  failed: "bg-red-100 text-red-900",
};

function formatDate(value: string | null) {
  if (!value) return "Em andamento";
  return new Date(value).toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  });
}

export default function CitizenAutomationMonitor() {
  const [token, setToken] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [status, setStatus] = useState("all");
  const [data, setData] = useState<RunPage | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(
        `${API}/content-admin/citizen-explanations?status=${status}&limit=50`,
        { headers: { Authorization: `Bearer ${accessToken}` }, cache: "no-store" },
      );
      if (response.status === 401 || response.status === 404) throw new Error("Acesso inválido.");
      if (!response.ok) throw new Error("Não foi possível consultar a automação.");
      setData(await response.json());
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, [accessToken, status]);

  useEffect(() => {
    void load();
  }, [load]);

  function enter(event: FormEvent) {
    event.preventDefault();
    setAccessToken(token.trim());
  }

  if (!accessToken) {
    return (
      <main id="conteudo" tabIndex={-1} className="min-h-screen bg-slate-100 px-5 py-16 text-slate-950">
        <Card className="mx-auto max-w-md p-7 shadow-sm">
          <p className="text-xs font-extrabold uppercase tracking-widest text-emerald-800">
            Monitor técnico
          </p>
          <h1 className="mt-3 text-3xl font-extrabold">Automação cidadã</h1>
          <p className="mt-3 leading-7 text-slate-600">
            Esta área apenas observa a esteira. Não há edição, aprovação ou publicação manual.
          </p>
          <form onSubmit={enter} className="mt-6">
            <input
              name="username"
              value="technical-monitor"
              readOnly
              autoComplete="username"
              tabIndex={-1}
              aria-hidden="true"
              className="sr-only"
            />
            <label htmlFor="token" className="text-sm font-bold">Token de monitoramento</label>
            <input
              id="token"
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              className="mt-2 min-h-11 w-full rounded border border-slate-300 px-4 outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
              autoComplete="current-password"
            />
            <button className="mt-4 min-h-11 w-full rounded bg-[#07152d] px-5 font-extrabold text-white hover:bg-slate-800">
              Abrir monitor
            </button>
          </form>
        </Card>
      </main>
    );
  }

  return (
    <main id="conteudo" tabIndex={-1} className="min-h-screen bg-slate-100 text-slate-950">
      <header className="bg-[#07152d] text-white">
        <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8">
          <p className="text-xs font-extrabold uppercase tracking-widest text-emerald-300">
            Operação autônoma
          </p>
          <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl font-extrabold sm:text-4xl">Monitor de explicações</h1>
              <p className="mt-2 max-w-2xl text-slate-300">
                Geração, duas validações e publicação acontecem sem intervenção humana.
              </p>
            </div>
            <button onClick={() => void load()} className="min-h-11 rounded border border-white/25 px-5 font-bold hover:bg-white/10">
              Atualizar dados
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
        {data && (
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Resumo da automação">
            {(Object.keys(labels) as RunStatus[]).map((key) => (
              <Card key={key} className="p-5">
                <p className="text-sm font-bold text-slate-500">{labels[key]}</p>
                <p className="mt-2 text-3xl font-extrabold">{data.counts[key]}</p>
              </Card>
            ))}
          </section>
        )}

        <Card className="mt-6 p-5">
          <div className="max-w-xs">
            <p className="mb-2 text-sm font-bold">Exibir tentativas</p>
            <FilterSelect
              id="status"
              label="Status"
              value={status}
              placeholder="Todos os resultados"
              placeholderValue="all"
              options={(Object.keys(labels) as RunStatus[]).map((value) => ({ value, label: labels[value] }))}
              onChange={setStatus}
            />
          </div>
        </Card>

        {error && <Card className="mt-6 border-red-200 bg-red-50 p-5 text-red-900">{error}</Card>}
        {loading && <p className="mt-6 font-bold text-slate-500">Carregando tentativas…</p>}
        {!loading && data?.items.length === 0 && (
          <Card className="mt-6 p-8 text-center text-slate-600">Nenhuma tentativa encontrada.</Card>
        )}
        <section className="mt-6 space-y-3" aria-label="Tentativas recentes">
          {data?.items.map((run) => (
            <Card key={run.id} className="p-5 sm:p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link href={`/proposicoes/${run.proposition_id}`} className="text-lg font-extrabold text-[#07152d] hover:text-emerald-800">
                      {run.label}
                    </Link>
                    <Badge className={colors[run.status]}>{labels[run.status]}</Badge>
                  </div>
                  <p className="mt-2 line-clamp-2 leading-6 text-slate-600">{run.summary}</p>
                </div>
                <p className="text-sm font-semibold text-slate-500">{formatDate(run.finished_at)}</p>
              </div>
              <div className="mt-5 grid gap-3 border-t border-slate-100 pt-4 text-sm sm:grid-cols-3">
                <div><span className="font-bold">Geração:</span> {run.generation_model}</div>
                <div><span className="font-bold">Verificação:</span> {run.verification_model}</div>
                <div><span className="font-bold">Versão:</span> {run.prompt_version}</div>
              </div>
              {run.error_code && (
                <p className="mt-3 rounded bg-slate-100 px-3 py-2 font-mono text-xs text-slate-700">
                  {run.error_code}
                </p>
              )}
            </Card>
          ))}
        </section>
      </div>
    </main>
  );
}
