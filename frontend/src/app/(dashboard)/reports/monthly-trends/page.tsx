"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid,
} from "recharts";
import type { ReportMonthlyTrends } from "@/lib/types";

const MONTH_OPTIONS = [
  { value: 3, label: "3 months" },
  { value: 6, label: "6 months" },
  { value: 12, label: "12 months" },
  { value: 24, label: "24 months" },
];

export default function MonthlyTrendsPage() {
  const [months, setMonths] = useState(12);
  const [data, setData] = useState<ReportMonthlyTrends | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // Intentional: load once on mount; user changes month count via buttons which call load() directly
    api.get<ReportMonthlyTrends>("/reports/monthly-trends", { months })
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-medium tracking-tight text-on-surface">Monthly Trends</h1>

      <Card>
        <div className="flex items-center gap-2">
          <span className="text-sm text-on-surface-variant">Show:</span>
          {MONTH_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              variant={months === opt.value ? "primary" : "secondary"}
              size="sm"
              onClick={() => {
                setMonths(opt.value);
                setLoading(true);
                setError("");
                api.get<ReportMonthlyTrends>("/reports/monthly-trends", { months: opt.value })
                  .then(setData)
                  .catch((e) => setError(e.detail ?? "Failed to load"))
                  .finally(() => setLoading(false));
              }}
            >
              {opt.label}
            </Button>
          ))}
        </div>
      </Card>

      {loading ? (
        <Card>
          <Skeleton className="h-80 w-full" />
        </Card>
      ) : error ? (
        <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>
      ) : data ? (
        <Card>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.data}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" />
                <XAxis dataKey="month" tick={{ fontSize: 12, fill: 'var(--color-on-surface-variant)' }} />
                <YAxis tick={{ fontSize: 12, fill: 'var(--color-on-surface-variant)' }} />
                <Tooltip content={<ChartTooltip formatter={(v) => formatCurrency(v)} />} />
                <Legend wrapperStyle={{ color: 'var(--color-on-surface-variant)' }} />
                <Line type="monotone" dataKey="income" stroke="#34a853" strokeWidth={2} name="Income" dot={false} />
                <Line type="monotone" dataKey="expenses" stroke="#ba1a1a" strokeWidth={2} name="Expenses" dot={false} />
                <Line type="monotone" dataKey="net" stroke="#005bbf" strokeWidth={2} name="Net" dot={false} strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
