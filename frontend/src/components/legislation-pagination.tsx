import { Button } from "@/components/ui/button";

type Props = {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
};

export function LegislationPagination({ page, pageSize, total, onPageChange }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total <= pageSize) return null;
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  return (
    <nav
      className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-slate-200 pt-6 sm:flex-row"
      aria-label="Paginação dos resultados"
    >
      <p className="text-sm text-slate-600">
        Exibindo <strong>{first}</strong>–<strong>{last}</strong> de <strong>{total}</strong>
      </p>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="secondary"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          ← Anterior
        </Button>
        <span className="min-w-24 text-center text-sm font-semibold text-slate-700">
          {page} de {pages}
        </span>
        <Button
          type="button"
          variant="secondary"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          Próxima →
        </Button>
      </div>
    </nav>
  );
}
