"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
import { ExportDialog } from "@/components/export/ExportDialog";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import type { ReportIncomeVsExpenses } from "@/lib/types";

export default function IncomeVsExpensesPage() {
  const [showExport, setShowExport] = useState(false);
  const today = new Date();
  const defaultFrom = new Date(today.getFullYear(), 0, 1).toISOString().split("T")[0];
  const defaultTo = today.toISOString().split("T")[0];

  const [dateFrom, setDateFrom] = useState(defaultFrom);
  const [dateTo, setDateTo] = useState(defaultTo);
  const [monthly, setMonthly] = useState(true);
  const [data, setData] = useState<ReportIncomeVsExpenses | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // Intentional: load once on mount with default dates; user triggers reload via Apply button
    api.get<ReportIncomeVsExpenses>("/reports/income-vs-expenses", {
      date_from: dateFrom, date_to: dateTo, monthly: monthly ? "true" : "false",
    })
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleApply = () => {
    setLoading(true);
    setError("");
    api.get<ReportIncomeVsExpenses>("/reports/income-vs-expenses", {
      date_from: dateFrom, date_to: dateTo, monthly: monthly ? "true" : "false",
    })
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  };

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  const chartData = data?.monthly_breakdown?.length
    ? data.monthly_breakdown.map((m) => ({
        month: m.month.slice(0, 7),
        Income: m.income,
        Expenses: m.expenses,
      }))
    : data
      ? [{ month: "Total", Income: data.total_income, Expenses: data.total_expenses }]
      : [];

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-medium tracking-tight text-on-surface">Income vs Expenses</h1>

      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <Input label="From" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <Input label="To" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          <label className="flex items-center gap-2 text-sm text-on-surface">
            <input type="checkbox" checked={monthly} onChange={(e) => setMonthly(e.target.checked)} className="accent-primary" />
            Monthly breakdown
          </label>
          <Button onClick={handleApply} loading={loading}>Apply</Button>
          <Button variant="tonal" onClick={() => setShowExport(true)}>Export</Button>
        </div>
      </Card>

      <ExportDialog open={showExport} onClose={() => setShowExport(false)} defaultReportType="income_vs_expenses" />

      {loading ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-outline-variant bg-surface p-6 space-y-4">
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-6 w-24" />
          </div>
          <div className="rounded-xl border border-outline-variant bg-surface p-6">
            <Skeleton className="h-64 w-full" />
          </div>
        </div>
      ) : error ? (
        <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>
      ) : data ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-on-surface-variant">Income</p>
                <p className="text-lg font-semibold text-success">{formatCurrency(data.total_income)}</p>
              </div>
              <div>
                <p className="text-xs text-on-surface-variant">Expenses</p>
                <p className="text-lg font-semibold text-error">{formatCurrency(data.total_expenses)}</p>
              </div>
              <div>
                <p className="text-xs text-on-surface-variant">Net</p>
                <p className={`text-lg font-semibold ${data.net >= 0 ? "text-success" : "text-error"}`}>{formatCurrency(data.net)}</p>
              </div>
            </div>
            <div className="mt-4">
              <Badge variant={data.net >= 0 ? "success" : "error"}>
                {data.net >= 0 ? "Surplus" : "Deficit"}
              </Badge>
            </div>
          </Card>

          <Card title="Chart">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <XAxis dataKey="month" tick={{ fontSize: 12, fill: 'var(--color-on-surface-variant)' }} />
                  <YAxis tick={{ fontSize: 12, fill: 'var(--color-on-surface-variant)' }} />
                  <Tooltip content={<ChartTooltip formatter={(v) => formatCurrency(v)} />} />
                  <Legend wrapperStyle={{ color: 'var(--color-on-surface-variant)' }} />
                  <Bar dataKey="Income" fill="#34a853" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Expenses" fill="#ba1a1a" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
