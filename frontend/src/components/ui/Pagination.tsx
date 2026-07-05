"use client";

interface PaginationProps {
  offset: number;
  limit: number;
  total: number;
  onChange: (offset: number) => void;
}

export function Pagination({ offset, limit, total, onChange }: PaginationProps) {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between pt-4">
      <p className="text-sm text-on-surface-variant">
        {offset + 1}–{Math.min(offset + limit, total)} of {total}
      </p>
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => onChange(0)}
          disabled={currentPage === 1}
          className="rounded-lg px-3 py-1.5 text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low disabled:opacity-30 transition-colors"
        >
          First
        </button>
        <button
          onClick={() => onChange(offset - limit)}
          disabled={currentPage === 1}
          className="rounded-lg px-3 py-1.5 text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low disabled:opacity-30 transition-colors"
        >
          Prev
        </button>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-sm font-medium text-primary">
          {currentPage}
        </span>
        <button
          onClick={() => onChange(offset + limit)}
          disabled={currentPage >= totalPages}
          className="rounded-lg px-3 py-1.5 text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low disabled:opacity-30 transition-colors"
        >
          Next
        </button>
        <button
          onClick={() => onChange((totalPages - 1) * limit)}
          disabled={currentPage >= totalPages}
          className="rounded-lg px-3 py-1.5 text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low disabled:opacity-30 transition-colors"
        >
          Last
        </button>
      </div>
    </div>
  );
}
