"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import type { ReportCategoryBreakdown } from "@/lib/types";

const COLORS = ["#005bbf", "#34a853", "#fbbc04", "#ba1a1a", "#8B5CF6", "#06B6D4", "#EC4899", "#84CC16", "#F97316", "#14B8A6", "#E11D48", "#A855F7"];

export default function CategoryBreakdownPage() {
  const today = new Date();
  const defaultFrom = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split("T")[0];
  const defaultTo = today.toISOString().split("T")[0];

  const [dateFrom, setDateFrom] = useState(defaultFrom);
  const [dateTo, setDateTo] = useState(defaultTo);
  const [data, setData] = useState<ReportCategoryBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // Intentional: load once on mount with default dates; user triggers reload via Apply button
    api.get<ReportCategoryBreakdown>("/reports/category-breakdown", { date_from: dateFrom, date_to: dateTo })
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleApply = () => {
    setLoading(true);
    setError("");
    api.get<ReportCategoryBreakdown>("/reports/category-breakdown", { date_from: dateFrom, date_to: dateTo })
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  };

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-medium tracking-tight text-on-surface">Category Breakdown</h1>

      <Card>
        <div className="flex items-end gap-4">
          <Input label="From" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <Input label="To" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          <Button onClick={handleApply} loading={loading}>Apply</Button>
        </div>
      </Card>

      {loading ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-outline-variant bg-surface p-6">
            <Skeleton className="h-80 w-full" />
          </div>
          <div className="rounded-xl border border-outline-variant bg-surface p-6 space-y-4">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-5 w-24" />
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-6 w-full" />
            ))}
          </div>
        </div>
      ) : error ? (
        <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>
      ) : data ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={data.categories} dataKey="total_amount" nameKey="category_name" cx="50%" cy="50%" outerRadius={100} label={{ fill: 'var(--color-on-surface-variant)', fontSize: 12 }}>
                    {data.categories.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip formatter={(v) => formatCurrency(v)} />} />
                  <Legend wrapperStyle={{ color: 'var(--color-on-surface-variant)' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card>
            <div className="space-y-4">
              <div className="flex justify-between text-sm">
                <span className="text-on-surface-variant">Total Income</span>
                <span className="font-semibold text-success">{formatCurrency(data.total_income)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-on-surface-variant">Total Expenses</span>
                <span className="font-semibold text-error">{formatCurrency(data.total_expenses)}</span>
              </div>
              <div className="flex justify-between text-sm border-t border-outline-variant pt-3">
                <span className="text-on-surface-variant">Net</span>
                <span className={`font-semibold ${data.net >= 0 ? "text-success" : "text-error"}`}>{formatCurrency(data.net)}</span>
              </div>
              <div className="mt-4 space-y-2">
                {data.categories.map((cat, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                      <span className="text-on-surface">{cat.category_name}</span>
                    </div>
                    <span className="font-medium text-on-surface">{formatCurrency(cat.total_amount)} ({cat.percentage.toFixed(1)}%)</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
