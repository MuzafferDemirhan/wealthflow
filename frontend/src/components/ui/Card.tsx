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
    <div className={clsx("rounded-xl border border-outline-variant bg-surface p-6", className)}>
      {(title || action) && (
        <div className="mb-5 flex items-center justify-between">
          {title && <h3 className="text-sm font-semibold text-on-surface">{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
