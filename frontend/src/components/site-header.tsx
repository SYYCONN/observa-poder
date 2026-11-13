"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";

const links = [
  ["Representantes", "/deputados"],
  ["Senadores", "/senadores"],
  ["Governadores", "/governadores"],
  ["Partidos", "/partidos"],
  ["Projetos", "/projetos"],
  ["Votações", "/votacoes"],
] as const;

export function SiteHeader() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="bg-white">
      <div className="border-b border-slate-200 bg-[#07152d] text-xs text-slate-200">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-2 sm:px-8">
          <p>Dados públicos, contexto e fontes verificáveis</p>
          <p className="hidden sm:block">Acompanhe o poder público brasileiro</p>
        </div>
      </div>
      <div className="border-b border-slate-200">
        <div className="mx-auto flex min-h-[78px] max-w-7xl items-center justify-between gap-5 px-5 sm:px-8">
          <Link
            href="/"
            aria-label="Observa Poder"
            className="shrink-0 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700"
          >
            <Image
              src="/brand/de-olho-na-politica.svg"
              alt="Observa Poder"
              width={114}
              height={72}
              priority
              className="h-14 w-[78px] object-contain object-left"
            />
          </Link>
          <nav
            className="hidden items-center gap-0.5 text-sm font-semibold text-slate-600 lg:flex"
            aria-label="Navegação principal"
          >
            {links.map(([label, href]) => {
              const active = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "border-b-2 border-transparent px-3 py-7 transition-colors hover:border-emerald-600 hover:text-[#07152d] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700",
                    active && "border-emerald-600 text-[#07152d]",
                  )}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
          <button
            type="button"
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMenuOpen((open) => !open)}
            className="inline-flex min-h-10 items-center rounded border border-slate-300 px-3 text-sm font-semibold text-[#07152d] hover:border-emerald-600 hover:text-emerald-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 lg:hidden"
          >
            {menuOpen ? "Fechar" : "Menu"}
          </button>
        </div>
      </div>
      {menuOpen && (
        <nav
          id="mobile-navigation"
          className="border-b border-slate-200 bg-white px-5 py-3 lg:hidden"
          aria-label="Navegação móvel"
        >
          <div className="mx-auto grid max-w-7xl gap-1 sm:grid-cols-2">
            {links.map(([label, href]) => {
              const active = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  onClick={() => setMenuOpen(false)}
                  className={cn(
                    "border-l-2 border-transparent px-3 py-3 text-sm font-semibold text-slate-700 hover:border-emerald-600 hover:bg-emerald-50 hover:text-[#07152d]",
                    active && "border-emerald-600 bg-emerald-50 text-[#07152d]",
                  )}
                >
                  {label}
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-slate-200 bg-[#07152d] text-slate-300">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-8 text-sm sm:px-8 md:flex-row md:items-start md:justify-between">
        <div className="max-w-xl space-y-2">
          <p className="font-semibold text-white">Observa Poder · informação pública com contexto.</p>
          <p className="text-slate-300">
            Projeto independente e sem fins lucrativos, criado para organizar dados públicos e
            facilitar o acompanhamento das decisões políticas. Não substitui as fontes oficiais.
          </p>
        </div>
        <nav aria-label="Transparência" className="flex flex-wrap gap-x-5 gap-y-3">
          <Link
            href="/sobre"
            className="rounded underline underline-offset-4 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300"
          >
            Sobre o projeto
          </Link>
          <Link
            href="/metodologia"
            className="rounded underline underline-offset-4 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300"
          >
            Metodologia e limites dos dados
          </Link>
          <Link
            href="/fontes-e-privacidade"
            className="rounded underline underline-offset-4 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300"
          >
            Fontes e privacidade
          </Link>
        </nav>
      </div>
    </footer>
  );
}
