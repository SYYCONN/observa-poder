import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sobre o projeto | Observa Poder",
  description:
    "Conheça o Observa Poder, um projeto independente e sem fins lucrativos para organizar dados públicos e facilitar o acompanhamento da política brasileira.",
};

export default function SobrePage() {
  return (
    <main className="mx-auto max-w-4xl px-5 py-14 sm:px-8 sm:py-20">
      <p className="text-xs font-bold uppercase tracking-[0.24em] text-emerald-700">Sobre o projeto</p>
      <h1 className="mt-4 text-4xl font-bold tracking-tight text-[#07152d] sm:text-5xl">
        Informação pública para acompanhar quem decide.
      </h1>
      <div className="mt-8 space-y-6 text-lg leading-8 text-slate-600">
        <p>
          O Observa Poder é um projeto independente e sem fins lucrativos. Organizamos registros
          publicados por órgãos públicos para tornar mais simples consultar representantes,
          projetos, votações e recursos públicos.
        </p>
        <p>
          Nosso trabalho é dar contexto, preservar a origem de cada registro e deixar claro quando
          uma informação ainda não foi coletada. A fonte oficial continua sendo a referência final
          para conferência e atualização.
        </p>
      </div>
      <section className="mt-12 rounded-2xl border border-slate-200 bg-slate-50 p-6 sm:p-8">
        <h2 className="text-xl font-semibold text-[#07152d]">Compromissos do Observa Poder</h2>
        <ul className="mt-4 space-y-3 text-slate-600">
          <li>• indicar a fonte e a data de coleta dos dados;</li>
          <li>• não inferir fatos que não estejam presentes no registro oficial;</li>
          <li>• explicar limites, lacunas e atualizações da base;</li>
          <li>• manter o acesso gratuito e sem finalidade comercial.</li>
        </ul>
      </section>
    </main>
  );
}
