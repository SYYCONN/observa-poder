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
    <main className="min-h-screen bg-slate-50">
      <SiteHeader />
      <section className="bg-slate-950 text-white">
        <div className="mx-auto max-w-7xl px-6 py-16">
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-300">{eyebrow}</p>
          <h1 className="mt-4 text-5xl font-extrabold tracking-tight">{title}</h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-300">{description}</p>
        </div>
      </section>
      <section className="mx-auto max-w-3xl px-6 py-20">
        <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">
            Próxima etapa de dados
          </p>
          <h2 className="mt-3 text-3xl font-extrabold text-slate-950">
            Estamos preparando esta consulta
          </h2>
          <p className="mt-4 leading-8 text-slate-600">
            A estrutura da seção já está definida. A integração será feita com a fonte oficial{" "}
            {source}, mantendo a data de coleta, o registro original e o contexto necessário para
            interpretar as informações.
          </p>
          <Link
            href="/"
            className="mt-8 inline-block rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white hover:bg-emerald-800"
          >
            Voltar ao início
          </Link>
        </div>
      </section>
      <SiteFooter />
    </main>
  );
}
