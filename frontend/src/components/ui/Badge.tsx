import { clsx } from "clsx";
import type { ReactNode } from "react";

type BadgeVariant = "success" | "warning" | "error" | "info" | "neutral";

const variantStyles: Record<BadgeVariant, string> = {
  success: "bg-success/15 text-success",
  warning: "bg-warning/15 text-warning",
  error: "bg-error/15 text-error",
  info: "bg-primary/10 text-primary",
  neutral: "bg-surface-container-high text-on-surface-variant",
};

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
}

export function Badge({ variant = "neutral", children, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
