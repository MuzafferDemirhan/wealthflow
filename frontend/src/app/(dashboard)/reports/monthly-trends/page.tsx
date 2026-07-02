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
      <h1 className="text-2xl font-bold tracking-tight">Monthly Trends</h1>

      <Card>
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-500">Show:</span>
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
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>
      ) : data ? (
        <Card>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.data}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-zinc-200 dark:stroke-zinc-800" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value) => formatCurrency(Number(value ?? 0))} />
                <Legend />
                <Line type="monotone" dataKey="income" stroke="#059669" strokeWidth={2} name="Income" dot={false} />
                <Line type="monotone" dataKey="expenses" stroke="#dc2626" strokeWidth={2} name="Expenses" dot={false} />
                <Line type="monotone" dataKey="net" stroke="#2563eb" strokeWidth={2} name="Net" dot={false} strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
