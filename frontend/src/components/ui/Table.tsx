"use client";

import { clsx } from "clsx";
import { Spinner } from "@/components/ui/Spinner";

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
  loading?: boolean;
  emptyMessage?: string;
  keyExtractor: (item: T) => string;
}

export function Table<T>({
  columns,
  data,
  onRowClick,
  loading,
  emptyMessage = "No data",
  keyExtractor,
}: TableProps<T>) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-text-muted">{emptyMessage}</div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border-light">
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx("px-4 py-3 font-medium text-text-muted", col.className)}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr
              key={keyExtractor(item)}
              onClick={() => onRowClick?.(item)}
              className={clsx(
                "border-b border-border-light transition-colors",
                onRowClick && "cursor-pointer hover:bg-surface-container-low",
              )}
            >
              {columns.map((col) => (
                <td key={col.key} className={clsx("px-4 py-3", col.className)}>
                  {col.render
                    ? col.render(item)
                    : (item as Record<string, unknown>)[col.key] as React.ReactNode}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
