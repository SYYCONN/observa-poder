"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { fetchPropositions, fetchVotings, Proposition, Voting } from "@/lib/api";

type Source = "camara" | "senado";

type Slide = {
  id: string;
  source: Source;
  image: string;
  institution: string;
  label: string;
  title: string;
  description: string;
  date: string;
  href: string;
};

const sourceInfo: Record<Source, { institution: string; image: string }> = {
  camara: { institution: "Câmara dos Deputados", image: "/hero/camara.png" },
  senado: { institution: "Senado Federal", image: "/hero/senado.png" },
};

function propositionSlide(item: Proposition): Slide {
  const source = item.source;
  const info = sourceInfo[source];
  return {
    id: `proposition-${item.id}`,
    source,
    image: info.image,
    institution: info.institution,
    label: `Agora na ${source === "camara" ? "Câmara" : "Senado"}`,
    title: `${item.kind} ${item.number ?? ""}/${item.year ?? ""}`.trim(),
    description: item.summary || "Proposição registrada na fonte oficial.",
    date: item.presented_at
      ? `Apresentada em ${item.presented_at}`
      : "Data de apresentação não informada",
    href: `/proposicoes/${item.id}`,
  };
}

function votingSlide(item: Voting): Slide {
  const source = item.source;
  const info = sourceInfo[source];
  return {
    id: `voting-${item.id}`,
    source,
    image: info.image,
    institution: info.institution,
    label: `Votação na ${source === "camara" ? "Câmara" : "no Senado"}`,
    title: item.object_description || item.description || "Votação registrada",
    description:
      item.approved === true
        ? "Resultado registrado: aprovada."
        : item.approved === false
          ? "Resultado registrado: rejeitada."
          : "Resultado ainda não classificado.",
    date: item.occurred_on ? `Realizada em ${item.occurred_on}` : "Data da votação não informada",
    href: `/votacoes/${item.id}`,
  };
}

const fallbackSlide: Slide = {
  id: "fallback",
  source: "camara",
  image: "/hero/brasilia.png",
  institution: "Congresso Nacional",
  label: "Acompanhe o Legislativo",
  title: "Projetos e votações em contexto",
  description: "Consulte os registros oficiais e entenda o que está em discussão.",
  date: "Dados atualizados pela fonte oficial",
  href: "/projetos",
};

export function InstitutionalCarousel() {
  const [propositions, setPropositions] = useState<Proposition[]>([]);
  const [votings, setVotings] = useState<Voting[]>([]);
  const [active, setActive] = useState(0);

  useEffect(() => {
    void Promise.allSettled([
      fetchPropositions("camara"),
      fetchPropositions("senado"),
      fetchVotings("camara"),
      fetchVotings("senado"),
    ]).then(([camaraPropositions, senadoPropositions, camaraVotings, senadoVotings]) => {
      setPropositions([
        ...(camaraPropositions.status === "fulfilled" ? camaraPropositions.value : []),
        ...(senadoPropositions.status === "fulfilled" ? senadoPropositions.value : []),
      ]);
      setVotings([
        ...(camaraVotings.status === "fulfilled" ? camaraVotings.value : []),
        ...(senadoVotings.status === "fulfilled" ? senadoVotings.value : []),
      ]);
    });
  }, []);

  const slides = useMemo(() => {
    const current = [
      ...propositions.slice(0, 4).map(propositionSlide),
      ...votings.slice(0, 4).map(votingSlide),
    ];
    return current.length > 0 ? current : [fallbackSlide];
  }, [propositions, votings]);

  useEffect(() => {
    if (active >= slides.length) setActive(0);
  }, [active, slides.length]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActive((current) => (current + 1) % slides.length);
    }, 8000);
    return () => window.clearInterval(timer);
  }, [slides.length]);

  const slide = slides[active] ?? fallbackSlide;
  const previous = () => setActive((current) => (current - 1 + slides.length) % slides.length);
  const next = () => setActive((current) => (current + 1) % slides.length);

  return (
    <aside
      className="relative mt-10 min-h-72 overflow-hidden rounded-md bg-[#07152d] lg:mt-0 lg:min-h-[31rem]"
      aria-label="O que está acontecendo no Legislativo"
    >
      {slides.map((item, index) => (
        <img
          key={item.id}
          src={item.image}
          alt=""
          aria-hidden={index !== active}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-700 motion-reduce:transition-none ${index === active ? "opacity-100" : "opacity-0"}`}
        />
      ))}
      <div className="absolute inset-0 bg-gradient-to-t from-[#07152d] via-[#07152d]/45 to-[#07152d]/10" />
      <div className="absolute inset-x-0 bottom-0 p-5 text-white sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.08em] text-emerald-300">
          {slide.label}
        </p>
        <h2 className="mt-2 text-xl font-semibold leading-tight">{slide.title}</h2>
        <p className="mt-2 line-clamp-3 text-sm leading-5 text-slate-200">{slide.description}</p>
        <p className="mt-2 text-xs text-slate-300">
          {slide.date} · {slide.institution}
        </p>
        <div className="mt-5 flex items-center justify-between gap-3">
          <Link
            href={slide.href}
            className="text-xs font-semibold text-emerald-300 underline decoration-emerald-300/60 underline-offset-4 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300"
          >
            Ver registro completo →
          </Link>
          <div className="flex items-center gap-1.5">
            <span className="text-xs tabular-nums text-slate-300">
              {active + 1}/{slides.length}
            </span>
            <button
              type="button"
              onClick={previous}
              aria-label="Registro anterior"
              className="inline-flex h-8 w-8 items-center justify-center rounded border border-white/50 text-sm hover:border-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300"
            >
              ←
            </button>
            <button
              type="button"
              onClick={next}
              aria-label="Próximo registro"
              className="inline-flex h-8 w-8 items-center justify-center rounded border border-white/50 text-sm hover:border-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300"
            >
              →
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
