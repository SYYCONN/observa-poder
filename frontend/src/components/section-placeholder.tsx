import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/site-header";

export function SectionPlaceholder({
  eyebrow,
  title,
  description,
  source,
}: {
  eyebrow: string;
  title: string;
  description: string;
  source: string;
}) {
  return (
    <main className="min-h-screen bg-[var(--paper)]">
      <SiteHeader />
      <section id="conteudo" tabIndex={-1} className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:py-16">
          <p className="text-sm font-semibold tracking-[0.08em] text-emerald-700">{eyebrow}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.03em] text-[#07152d] sm:text-5xl">
            {title}
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">{description}</p>
        </div>
      </section>
      <section className="mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:py-16">
        <div className="border-y border-slate-200 bg-white px-6 py-8 sm:px-8">
          <p className="text-sm font-semibold tracking-[0.08em] text-emerald-700">
            Próxima etapa de dados
          </p>
          <h2 className="mt-3 text-2xl font-semibold text-[#07152d]">
            Esta consulta está sendo preparada.
          </h2>
          <p className="mt-4 max-w-3xl leading-7 text-slate-600">
            A integração será feita com a fonte oficial {source}, mantendo a data de coleta, o
            registro original e o contexto necessário para interpretar as informações.
          </p>
          <Link
            href="/"
            className="mt-7 inline-flex font-semibold text-emerald-800 underline decoration-emerald-300 underline-offset-4 hover:text-[#07152d]"
          >
            Voltar ao início →
          </Link>
        </div>
      </section>
      <SiteFooter />
    </main>
  );
}
