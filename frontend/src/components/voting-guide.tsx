const terms = [
  [
    "Votação nominal",
    "Identifica a posição registrada de cada parlamentar. A lista do portal mostra somente os registros publicados pela fonte e incorporados à coleta.",
  ],
  [
    "Votação simbólica",
    "O resultado é proclamado a partir da manifestação dos parlamentares, sem o mesmo registro individual de uma votação nominal. Ausência de votos na base consultada, sozinha, não comprova essa modalidade.",
  ],
  [
    "Modalidade não informada",
    "Os dados coletados não permitem identificar como ocorreu a votação. Isso não significa que ninguém votou nem que houve unanimidade.",
  ],
  [
    "Aprovada ou rejeitada",
    "É o resultado da decisão descrita nesta etapa. Aprovar um requerimento, uma emenda ou uma etapa não significa que o projeto inteiro virou lei.",
  ],
  [
    "Requerimento (REQ)",
    "É um pedido formal no processo legislativo, como solicitar informações ou uma providência. Seu conteúdo deve ser consultado na proposição relacionada.",
  ],
  [
    "Outros registros",
    "Agrupa posições diferentes de Sim e Não, como abstenção e obstrução, quando publicadas. Abstenção é a opção de não escolher uma das alternativas; obstrução é um recurso para impedir ou adiar a deliberação. As demais siglas são preservadas como vieram da fonte.",
  ],
];

export function VotingGuide() {
  return (
    <details className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
      <summary className="cursor-pointer rounded text-base font-bold text-emerald-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700">
        Entenda as votações: modalidades, resultados e termos
      </summary>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        Este guia ajuda a ler os registros. Dados ausentes não são tratados como zero, ausência do
        parlamentar ou voto contrário.
      </p>
      <dl className="mt-5 grid gap-5 sm:grid-cols-2">
        {terms.map(([term, description]) => (
          <div key={term}>
            <dt className="font-bold text-slate-950">{term}</dt>
            <dd className="mt-1 text-sm leading-6 text-slate-600">{description}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-5 border-t border-slate-100 pt-4 text-sm text-slate-600">
        Referências:{" "}
        <a
          className="font-semibold text-emerald-800 underline"
          href="https://www2.camara.leg.br/comunicacao/assessoria-de-imprensa/guia-para-jornalistas/votacao"
          target="_blank"
          rel="noreferrer"
        >
          guia da Câmara
        </a>
        {" e "}
        <a
          className="font-semibold text-emerald-800 underline"
          href="https://www.congressonacional.leg.br/legislacao-e-publicacoes/glossario-legislativo"
          target="_blank"
          rel="noreferrer"
        >
          glossário do Congresso Nacional
        </a>
        .
      </p>
    </details>
  );
}
