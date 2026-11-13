import Link from "next/link";
import { InstitutionalCarousel } from "@/components/institutional-carousel";

const quickLinks = [
  ["Deputados", "Câmara dos Deputados", "/deputados"],
  ["Senadores", "Senado Federal", "/senadores"],
  ["Projetos", "Propostas em tramitação", "/projetos"],
  ["Votações", "Resultados e votos nominais", "/votacoes"],
] as const;

export function HeroBanner() {
  return (
    <section className="border-b border-slate-200 bg-white">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 sm:px-8 lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-12">
        <div className="max-w-4xl py-12 sm:py-16 lg:py-20">
          <h1 className="max-w-3xl text-4xl font-semibold leading-[1.05] tracking-[-0.035em] text-[#07152d] sm:text-5xl lg:text-[4.25rem]">
            Representantes, projetos e votações no Brasil
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
            Consulte registros da Câmara dos Deputados e do Senado Federal. Confira a origem e o
            período de referência dos dados em cada consulta.
          </p>
          <form
            action="/pesquisa"
            method="get"
            className="mt-8 flex max-w-2xl flex-col gap-3 sm:flex-row"
            role="search"
          >
            <label className="sr-only" htmlFor="home-search">
              Pesquisar no portal
            </label>
            <input
              id="home-search"
              name="q"
              type="search"
              placeholder="Buscar parlamentar, projeto ou votação"
              className="min-h-12 flex-1 rounded border border-slate-300 bg-white px-4 text-base text-[#07152d] outline-none placeholder:text-slate-400 focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
            />
            <button
              type="submit"
              className="min-h-12 rounded bg-[#07152d] px-6 text-sm font-semibold text-white transition hover:bg-[#102a50] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700"
            >
              Pesquisar
            </button>
          </form>
        </div>
        <InstitutionalCarousel />
      </div>
      <nav className="border-t border-slate-200 bg-[#f4f7f8]" aria-label="Acesso rápido">
        <div className="mx-auto grid max-w-7xl sm:grid-cols-2 lg:grid-cols-4">
          {quickLinks.map(([label, description, href]) => (
            <Link
              key={href}
              href={href}
              className="group flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-4 transition-colors hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-700 sm:px-8 lg:border-b-0 lg:border-r lg:last:border-r-0"
            >
              <span>
                <span className="block text-sm font-semibold text-[#07152d] group-hover:text-emerald-800">
                  {label}
                </span>
                <span className="mt-1 block text-xs text-slate-500">{description}</span>
              </span>
              <span className="text-lg text-emerald-700" aria-hidden="true">
                →
              </span>
            </Link>
          ))}
        </div>
      </nav>
    </section>
  );
}
