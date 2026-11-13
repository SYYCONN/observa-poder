"use client";

import { useEffect, useState } from "react";

const slides = [
  {
    image: "/hero/brasilia.png",
    title: "Brasília",
    description: "Sede dos poderes da República",
    institution: null,
  },
  {
    image: "/hero/camara.png",
    title: "Câmara dos Deputados",
    description: "Projetos, debates e votações da Câmara",
    institution: "camara",
  },
  {
    image: "/hero/senado.png",
    title: "Senado Federal",
    description: "Proposições e decisões do Senado",
    institution: "senado",
  },
] as const;

export function InstitutionalCarousel({
  preferredSource,
}: {
  preferredSource?: "camara" | "senado" | null;
}) {
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (!preferredSource) return;
    const nextIndex = slides.findIndex((slide) => slide.institution === preferredSource);
    if (nextIndex >= 0) setActive(nextIndex);
  }, [preferredSource]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActive((current) => (current + 1) % slides.length);
    }, 7000);
    return () => window.clearInterval(timer);
  }, []);

  const slide = slides[active];
  const previous = () => setActive((current) => (current - 1 + slides.length) % slides.length);
  const next = () => setActive((current) => (current + 1) % slides.length);

  return (
    <aside
      className="relative mt-10 min-h-72 overflow-hidden rounded-md bg-[#07152d] lg:mt-0 lg:min-h-[31rem]"
      aria-label="Imagens institucionais"
    >
      {slides.map((item, index) => (
        <img
          key={item.image}
          src={item.image}
          alt=""
          aria-hidden={index !== active}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-700 ${index === active ? "opacity-100" : "opacity-0"}`}
        />
      ))}
      <div className="absolute inset-0 bg-gradient-to-t from-[#07152d]/95 via-[#07152d]/15 to-[#07152d]/10" />
      <div className="absolute inset-x-0 bottom-0 p-5 text-white sm:p-6">
        <p className="text-sm font-semibold">{slide.title}</p>
        <p className="mt-1 text-xs text-slate-300">{slide.description}</p>
        <div className="mt-5 flex items-center justify-between gap-3">
          <div className="flex gap-1.5" aria-label="Selecionar imagem">
            {slides.map((item, index) => (
              <button
                key={item.image}
                type="button"
                aria-label={`Mostrar imagem ${index + 1}: ${item.title}`}
                aria-pressed={index === active}
                onClick={() => setActive(index)}
                className={`h-1.5 rounded-full transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300 ${index === active ? "w-8 bg-emerald-300" : "w-3 bg-white/50 hover:bg-white"}`}
              />
            ))}
          </div>
          <div className="flex gap-1.5">
            <button
              type="button"
              onClick={previous}
              aria-label="Imagem anterior"
              className="inline-flex h-8 w-8 items-center justify-center rounded border border-white/50 text-sm hover:border-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300"
            >
              ←
            </button>
            <button
              type="button"
              onClick={next}
              aria-label="Próxima imagem"
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
