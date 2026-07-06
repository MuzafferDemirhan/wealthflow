import type { CSSProperties } from "react";

interface ChartTooltipPayloadEntry {
  name: string;
  value: number;
  color: string;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: ChartTooltipPayloadEntry[];
  label?: string;
  formatter?: (value: number) => string;
}

export function ChartTooltip({ active, payload, label, formatter }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const style: CSSProperties = {
    backgroundColor: "var(--color-surface)",
    border: "1px solid var(--color-outline-variant)",
    borderRadius: "0.75rem",
    padding: "0.75rem 1rem",
    boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
  };

  return (
    <div style={style}>
      {label && (
        <p className="mb-1 text-xs font-medium text-on-surface-variant">{label}</p>
      )}
      {payload.map((entry, i) => (
        <p key={i} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: {formatter ? formatter(entry.value) : entry.value}
        </p>
      ))}
    </div>
  );
}
