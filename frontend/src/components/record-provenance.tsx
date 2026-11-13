const collectionDateFormat = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "America/Sao_Paulo",
});

const sourceNames: Record<string, string> = {
  camara: "Câmara dos Deputados",
  senado: "Senado Federal",
};

export function RecordProvenance({
  source,
  externalId,
  collectedAt,
}: {
  source: string;
  externalId: string;
  collectedAt: string;
}) {
  const date = new Date(collectedAt);

  return (
    <dl className="mt-6 flex flex-wrap gap-x-8 gap-y-3 text-sm text-slate-300">
      <div>
        <dt className="font-semibold">Fonte</dt>
        <dd>{sourceNames[source] ?? "Órgão não informado"}</dd>
      </div>
      <div className="min-w-0">
        <dt className="font-semibold">Identificador na fonte</dt>
        <dd className="wrap-anywhere">{externalId || "Não informado"}</dd>
      </div>
      <div>
        <dt className="font-semibold">Coleta deste registro</dt>
        <dd>
          {Number.isNaN(date.getTime()) ? (
            "Data não informada"
          ) : (
            <>
              <time dateTime={date.toISOString()}>{collectionDateFormat.format(date)}</time>
              {" (horário de Brasília)"}
            </>
          )}
        </dd>
      </div>
    </dl>
  );
}
