"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
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

  if (loading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-9 w-40" />
        <div className="grid gap-5 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-outline-variant bg-surface p-6 space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-8 w-32" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) return <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>;
  if (!data) return null;

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-medium tracking-tight text-on-surface">Net Worth</h1>

      <div className="grid gap-5 sm:grid-cols-3">
        <Card>
          <p className="text-xs text-on-surface-variant">Total Assets</p>
          <p className="text-2xl font-semibold text-success">{formatCurrency(data.total_assets)}</p>
        </Card>
        <Card>
          <p className="text-xs text-on-surface-variant">Total Liabilities</p>
          <p className="text-2xl font-semibold text-error">{formatCurrency(data.total_liabilities)}</p>
        </Card>
        <Card>
          <p className="text-xs text-on-surface-variant">Net Worth</p>
          <p className={`text-2xl font-semibold ${data.net_worth >= 0 ? "text-on-surface" : "text-error"}`}>
            {formatCurrency(data.net_worth)}
          </p>
          <p className="text-xs text-on-surface-variant">as of {data.as_of_date}</p>
        </Card>
      </div>

      {data.portfolio_market_value > 0 && (
        <Card title="Portfolio">
          <p className="text-sm text-on-surface">Market Value: <span className="font-semibold">{formatCurrency(data.portfolio_market_value)}</span></p>
        </Card>
      )}

      <Card title="Breakdown by Account Type">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Type</th>
                <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Count</th>
                <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Total Balance</th>
              </tr>
            </thead>
            <tbody>
              {data.by_account_type.map((item, i) => (
                <tr key={i} className="border-t border-outline-variant/50">
                  <td className="py-3 pr-4">
                    <Badge variant="neutral">{item.account_type.replace(/_/g, " ")}</Badge>
                  </td>
                  <td className="py-3 pr-4 text-on-surface">{item.count}</td>
                  <td className="py-3 font-semibold text-on-surface">{formatCurrency(item.total_balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
