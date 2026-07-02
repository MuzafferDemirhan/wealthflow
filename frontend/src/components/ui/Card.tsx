import type { ReactNode } from "react";
import { clsx } from "clsx";

interface CardProps {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Card({ title, action, children, className }: CardProps) {
  return (
    <div className={clsx("rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950", className)}>
      {(title || action) && (
        <div className="flex items-center justify-between border-b border-zinc-200 px-5 py-3 dark:border-zinc-800">
          {title && <h3 className="text-sm font-semibold">{title}</h3>}
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}
