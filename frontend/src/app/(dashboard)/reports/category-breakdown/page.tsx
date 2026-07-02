"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import type { ReportCategoryBreakdown } from "@/lib/types";

const COLORS = ["#059669", "#2563eb", "#d97706", "#dc2626", "#7c3aed", "#0891b2", "#be123c", "#84cc16", "#f97316", "#14b8a6", "#e11d48", "#8b5cf6"];

export default function CategoryBreakdownPage() {
  const today = new Date();
  const defaultFrom = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split("T")[0];
  const defaultTo = today.toISOString().split("T")[0];

  const [dateFrom, setDateFrom] = useState(defaultFrom);
  const [dateTo, setDateTo] = useState(defaultTo);
  const [data, setData] = useState<ReportCategoryBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = (from: string, to: string) => {
    setLoading(true);
    setError("");
    api.get<ReportCategoryBreakdown>("/reports/category-breakdown", { date_from: from, date_to: to })
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(dateFrom, dateTo); }, []);

  const handleApply = () => load(dateFrom, dateTo);

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Category Breakdown</h1>

      <Card>
        <div className="flex items-end gap-4">
          <Input label="From" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <Input label="To" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
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
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={data.categories} dataKey="total_amount" nameKey="category_name" cx="50%" cy="50%" outerRadius={100} label>
                    {data.categories.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatCurrency(Number(value ?? 0))} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-zinc-500">Total Income</span>
                <span className="font-semibold text-emerald-600">{formatCurrency(data.total_income)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-zinc-500">Total Expenses</span>
                <span className="font-semibold text-red-600">{formatCurrency(data.total_expenses)}</span>
              </div>
              <div className="flex justify-between text-sm border-t pt-2 dark:border-zinc-800">
                <span className="text-zinc-500">Net</span>
                <span className={`font-semibold ${data.net >= 0 ? "text-emerald-600" : "text-red-600"}`}>{formatCurrency(data.net)}</span>
              </div>
              <div className="mt-4 space-y-2">
                {data.categories.map((cat, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                      <span>{cat.category_name}</span>
                    </div>
                    <span className="font-medium">{formatCurrency(cat.total_amount)} ({cat.percentage.toFixed(1)}%)</span>
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
