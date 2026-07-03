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

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#EC4899", "#84CC16", "#F97316", "#14B8A6", "#E11D48", "#A855F7"];

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
      <h1 className="text-2xl font-bold tracking-tight text-text-primary">Category Breakdown</h1>

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
        <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>
      ) : data ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={data.categories} dataKey="total_amount" nameKey="category_name" cx="50%" cy="50%" outerRadius={100} label={{ fill: '#94A3B8', fontSize: 12 }}>
                    {data.categories.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: '8px', color: '#F8FAFC' }} formatter={(value) => formatCurrency(Number(value ?? 0))} />
                  <Legend wrapperStyle={{ color: '#94A3B8' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">Total Income</span>
                <span className="font-semibold text-success">{formatCurrency(data.total_income)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">Total Expenses</span>
                <span className="font-semibold text-error">{formatCurrency(data.total_expenses)}</span>
              </div>
              <div className="flex justify-between text-sm border-t pt-2 border-border-light">
                <span className="text-text-muted">Net</span>
                <span className={`font-semibold ${data.net >= 0 ? "text-success" : "text-error"}`}>{formatCurrency(data.net)}</span>
              </div>
              <div className="mt-4 space-y-2">
                {data.categories.map((cat, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                      <span className="text-text-primary">{cat.category_name}</span>
                    </div>
                    <span className="font-medium text-text-primary">{formatCurrency(cat.total_amount)} ({cat.percentage.toFixed(1)}%)</span>
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
