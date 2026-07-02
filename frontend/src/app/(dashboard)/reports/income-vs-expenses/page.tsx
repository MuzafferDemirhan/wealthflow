"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import type { ReportIncomeVsExpenses } from "@/lib/types";

export default function IncomeVsExpensesPage() {
  const today = new Date();
  const defaultFrom = new Date(today.getFullYear(), 0, 1).toISOString().split("T")[0];
  const defaultTo = today.toISOString().split("T")[0];

  const [dateFrom, setDateFrom] = useState(defaultFrom);
  const [dateTo, setDateTo] = useState(defaultTo);
  const [monthly, setMonthly] = useState(true);
  const [data, setData] = useState<ReportIncomeVsExpenses | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = (from: string, to: string, isMonthly: boolean) => {
    setLoading(true);
    setError("");
    api.get<ReportIncomeVsExpenses>("/reports/income-vs-expenses", {
      date_from: from, date_to: to, monthly: isMonthly ? "true" : "false",
    })
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(dateFrom, dateTo, monthly); }, []);

  const handleApply = () => load(dateFrom, dateTo, monthly);

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
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Income vs Expenses</h1>

      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <Input label="From" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <Input label="To" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={monthly} onChange={(e) => setMonthly(e.target.checked)} />
            Monthly breakdown
          </label>
          <Button onClick={handleApply} loading={loading}>Apply</Button>
        </div>
      </Card>

      {loading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : error ? (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>
      ) : data ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-zinc-500">Income</p>
                <p className="text-lg font-semibold text-emerald-600">{formatCurrency(data.total_income)}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500">Expenses</p>
                <p className="text-lg font-semibold text-red-600">{formatCurrency(data.total_expenses)}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500">Net</p>
                <p className={`text-lg font-semibold ${data.net >= 0 ? "text-emerald-600" : "text-red-600"}`}>{formatCurrency(data.net)}</p>
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
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value) => formatCurrency(Number(value ?? 0))} />
                  <Legend />
                  <Bar dataKey="Income" fill="#059669" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Expenses" fill="#dc2626" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
