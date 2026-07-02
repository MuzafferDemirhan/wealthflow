"use client";

import { clsx } from "clsx";

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

  const pages: number[] = [];
  for (let i = 1; i <= totalPages; i++) {
    pages.push(i);
  }

  return (
    <div className="flex items-center justify-between px-4 py-3">
      <p className="text-sm text-zinc-500">
        {offset + 1}–{Math.min(offset + limit, total)} of {total}
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange(0)}
          disabled={currentPage === 1}
          className="rounded px-2 py-1 text-sm text-zinc-500 hover:text-zinc-900 disabled:opacity-30 dark:hover:text-zinc-50"
        >
          First
        </button>
        <button
          onClick={() => onChange(offset - limit)}
          disabled={currentPage === 1}
          className="rounded px-2 py-1 text-sm text-zinc-500 hover:text-zinc-900 disabled:opacity-30 dark:hover:text-zinc-50"
        >
          Prev
        </button>
        <span className="px-2 text-sm font-medium">{currentPage}</span>
        <button
          onClick={() => onChange(offset + limit)}
          disabled={currentPage >= totalPages}
          className="rounded px-2 py-1 text-sm text-zinc-500 hover:text-zinc-900 disabled:opacity-30 dark:hover:text-zinc-50"
        >
          Next
        </button>
        <button
          onClick={() => onChange((totalPages - 1) * limit)}
          disabled={currentPage >= totalPages}
          className="rounded px-2 py-1 text-sm text-zinc-500 hover:text-zinc-900 disabled:opacity-30 dark:hover:text-zinc-50"
        >
          Last
        </button>
      </div>
    </div>
  );
}
