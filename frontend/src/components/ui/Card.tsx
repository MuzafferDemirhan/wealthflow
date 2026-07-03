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
    <div className={clsx("rounded-xl bg-surface-bright border border-border", className)}>
      {(title || action) && (
        <div className="flex items-center justify-between border-b border-border-light px-5 py-3">
          {title && <h3 className="text-sm font-semibold text-text-primary">{title}</h3>}
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}
