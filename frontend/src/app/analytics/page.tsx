"use client";

import { FormEvent, useState } from "react";

type Metric = {
  day: string;
  category: string;
  route: string;
  outcome: string;
  count: number;
  average_duration_ms: number;
};
const integrationStatus = {
  running: "Em execução",
  success: "Concluída",
  failed: "Falhou",
  interrupted: "Interrompida",
};

type IntegrationHealth = {
  job: string;
  label: string;
  latest_status: keyof typeof integrationStatus | null;
  latest_started_at: string | null;
  last_success_at: string | null;
  failures_last_7_days: number;
};

type Summary = { start: string; end: string; items: Metric[]; integrations: IntegrationHealth[] };

const dateTime = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "America/Sao_Paulo",
});

export default function AnalyticsDashboard() {
  const [token, setToken] = useState("");
  const [days, setDays] = useState("30");
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setData(null);
    try {
      const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
      const response = await fetch(`${api}/analytics/summary?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
        credentials: "omit",
        referrerPolicy: "no-referrer",
      });
      if (!response.ok)
        throw new Error(
          response.status === 401
            ? "Token inválido."
            : "Painel indisponível. Confira a configuração e o período.",
        );
      setData((await response.json()) as Summary);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível carregar o painel.");
    } finally {
      setBusy(false);
    }
  }

  const total = (category: string) =>
    data?.items
      .filter((row) => row.category === category)
      .reduce((sum, row) => sum + row.count, 0) ?? 0;
  const errors =
    data?.items
      .filter((row) => row.category === "api_request" && Number(row.outcome) >= 500)
      .reduce((sum, row) => sum + row.count, 0) ?? 0;

  return (
    <main id="conteudo" tabIndex={-1} className="mx-auto max-w-6xl space-y-6 p-4 sm:p-8">
      <h1 className="text-2xl font-bold">Analytics · acesso restrito</h1>
      <p>
        Contadores agregados em America/Sao_Paulo. Visualizações e requisições não representam
        pessoas únicas.
      </p>
      <form onSubmit={load} className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1">
          Token administrativo
          <input
            type="password"
            autoComplete="off"
            required
            value={token}
            onChange={(event) => setToken(event.target.value)}
            className="rounded border p-2"
          />
        </label>
        <label className="flex flex-col gap-1">
          Últimos dias
          <input
            type="number"
            min="1"
            max="366"
            required
            value={days}
            onChange={(event) => setDays(event.target.value)}
            className="w-24 rounded border p-2"
          />
        </label>
        <button disabled={busy} className="rounded bg-emerald-800 p-2 text-white">
          {busy ? "Carregando…" : "Consultar"}
        </button>
        <button
          type="button"
          onClick={() => {
            setToken("");
            setData(null);
            setError("");
          }}
          className="rounded border p-2"
        >
          Limpar acesso
        </button>
      </form>
      <p className="text-sm text-slate-600">
        O token fica somente na memória desta página. Nenhuma credencial é salva no navegador.
      </p>
      {error && <p role="alert">{error}</p>}
      {data && (
        <>
          <h2 className="text-xl font-semibold">Uso e desempenho</h2>
          <p>
            {data.start} a {data.end}
          </p>
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ["Visualizações", total("pageview")],
              ["Buscas na API", total("search_request")],
              ["Filtros na API", total("filter_request")],
              ["PDFs servidos", total("download")],
              ["Requisições da API", total("api_request")],
              ["Erros 5xx", errors],
            ].map(([label, value]) => (
              <div key={label} className="rounded border p-4">
                <p>{label}</p>
                <strong className="text-2xl">{value}</strong>
              </div>
            ))}
          </div>
          <p className="text-sm">
            Buscas e filtros incluem paginação e chamadas técnicas com esses parâmetros. Downloads
            indicam respostas bem-sucedidas, sem confirmação de salvamento. Bloqueadores e robôs
            afetam os números.
          </p>
          {!data.items.length ? (
            <p>Nenhum contador no período.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <caption className="sr-only">
                  Contadores por dia, categoria, rota e resultado
                </caption>
                <thead>
                  <tr>
                    {["Dia", "Categoria", "Rota", "Resultado", "Total", "Média ms"].map((label) => (
                      <th key={label} className="border-b p-2">
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row) => (
                    <tr key={`${row.day}-${row.category}-${row.route}-${row.outcome}`}>
                      <td className="p-2">{row.day}</td>
                      <td className="p-2">{row.category}</td>
                      <td className="p-2">{row.route}</td>
                      <td className="p-2">{row.outcome}</td>
                      <td className="p-2">{row.count}</td>
                      <td className="p-2">{row.average_duration_ms}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <section aria-labelledby="integration-health-title" className="space-y-3">
            <h2 id="integration-health-title" className="text-xl font-semibold">
              Saúde das integrações
            </h2>
            <p className="text-sm">
              Compare o último sucesso com a frequência de cada coleta. As falhas e interrupções
              dos últimos 7 dias aparecem mesmo quando uma tentativa posterior foi concluída.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr>
                    {[
                      "Integração",
                      "Última tentativa",
                      "Início da tentativa",
                      "Último sucesso",
                      "Falhas em 7 dias",
                    ].map((label) => (
                      <th key={label} scope="col" className="border-b p-2">
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.integrations.map((integration) => (
                    <tr key={integration.job}>
                      <th scope="row" className="p-2 font-medium">
                        {integration.label}
                      </th>
                      <td className="p-2">
                        {integration.latest_status
                          ? integrationStatus[integration.latest_status]
                          : "Sem registro"}
                      </td>
                      <td className="p-2">
                        {integration.latest_started_at
                          ? dateTime.format(new Date(integration.latest_started_at))
                          : "—"}
                      </td>
                      <td className="p-2">
                        {integration.last_success_at
                          ? dateTime.format(new Date(integration.last_success_at))
                          : "—"}
                      </td>
                      <td className="p-2">
                        {integration.latest_status ? integration.failures_last_7_days : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
