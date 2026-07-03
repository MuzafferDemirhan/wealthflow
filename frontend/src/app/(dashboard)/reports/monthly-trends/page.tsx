"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
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

  const load = (m: number) => {
    setLoading(true);
    setError("");
    api.get<ReportMonthlyTrends>("/reports/monthly-trends", { months: m })
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(months); }, []);

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight text-text-primary">Monthly Trends</h1>

      <Card>
        <div className="flex items-center gap-2">
          <span className="text-sm text-text-muted">Show:</span>
          {MONTH_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              variant={months === opt.value ? "primary" : "secondary"}
              size="sm"
              onClick={() => { setMonths(opt.value); load(opt.value); }}
            >
              {opt.label}
            </Button>
          ))}
        </div>
      </Card>

      {loading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : error ? (
        <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>
      ) : data ? (
        <Card>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#94A3B8' }} />
                <YAxis tick={{ fontSize: 12, fill: '#94A3B8' }} />
                <Tooltip contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: '8px', color: '#F8FAFC' }} formatter={(value) => formatCurrency(Number(value ?? 0))} />
                <Legend wrapperStyle={{ color: '#94A3B8' }} />
                <Line type="monotone" dataKey="income" stroke="#10B981" strokeWidth={2} name="Income" dot={false} />
                <Line type="monotone" dataKey="expenses" stroke="#EF4444" strokeWidth={2} name="Expenses" dot={false} />
                <Line type="monotone" dataKey="net" stroke="#3B82F6" strokeWidth={2} name="Net" dot={false} strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
