"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import type { ReportNetWorth } from "@/lib/types";

export default function NetWorthPage() {
  const [data, setData] = useState<ReportNetWorth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<ReportNetWorth>("/reports/net-worth")
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  if (loading) return <div className="flex justify-center py-12"><Spinner size="lg" /></div>;
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Net Worth</h1>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-xs text-zinc-500">Total Assets</p>
          <p className="text-2xl font-bold text-emerald-600">{formatCurrency(data.total_assets)}</p>
        </Card>
        <Card>
          <p className="text-xs text-zinc-500">Total Liabilities</p>
          <p className="text-2xl font-bold text-red-600">{formatCurrency(data.total_liabilities)}</p>
        </Card>
        <Card>
          <p className="text-xs text-zinc-500">Net Worth</p>
          <p className={`text-2xl font-bold ${data.net_worth >= 0 ? "text-zinc-900 dark:text-zinc-50" : "text-red-600"}`}>
            {formatCurrency(data.net_worth)}
          </p>
          <p className="text-xs text-zinc-500">as of {data.as_of_date}</p>
        </Card>
      </div>

      {data.portfolio_market_value > 0 && (
        <Card title="Portfolio">
          <p className="text-sm">Market Value: <span className="font-semibold">{formatCurrency(data.portfolio_market_value)}</span></p>
        </Card>
      )}

      <Card title="Breakdown by Account Type">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-200 dark:border-zinc-800">
                <th className="px-4 py-3 font-medium text-zinc-500">Type</th>
                <th className="px-4 py-3 font-medium text-zinc-500">Count</th>
                <th className="px-4 py-3 font-medium text-zinc-500">Total Balance</th>
              </tr>
            </thead>
            <tbody>
              {data.by_account_type.map((item, i) => (
                <tr key={i} className="border-b border-zinc-100 dark:border-zinc-800/50">
                  <td className="px-4 py-3">
                    <Badge>{item.account_type.replace(/_/g, " ")}</Badge>
                  </td>
                  <td className="px-4 py-3">{item.count}</td>
                  <td className="px-4 py-3 font-semibold">{formatCurrency(item.total_balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
