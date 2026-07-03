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
  if (error) return <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight text-text-primary">Net Worth</h1>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-xs text-text-muted">Total Assets</p>
          <p className="text-2xl font-bold text-success">{formatCurrency(data.total_assets)}</p>
        </Card>
        <Card>
          <p className="text-xs text-text-muted">Total Liabilities</p>
          <p className="text-2xl font-bold text-error">{formatCurrency(data.total_liabilities)}</p>
        </Card>
        <Card>
          <p className="text-xs text-text-muted">Net Worth</p>
          <p className={`text-2xl font-bold ${data.net_worth >= 0 ? "text-text-primary" : "text-error"}`}>
            {formatCurrency(data.net_worth)}
          </p>
          <p className="text-xs text-text-muted">as of {data.as_of_date}</p>
        </Card>
      </div>

      {data.portfolio_market_value > 0 && (
        <Card title="Portfolio">
          <p className="text-sm text-text-primary">Market Value: <span className="font-semibold">{formatCurrency(data.portfolio_market_value)}</span></p>
        </Card>
      )}

      <Card title="Breakdown by Account Type">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border-light">
                <th className="px-4 py-3 font-medium text-text-muted">Type</th>
                <th className="px-4 py-3 font-medium text-text-muted">Count</th>
                <th className="px-4 py-3 font-medium text-text-muted">Total Balance</th>
              </tr>
            </thead>
            <tbody>
              {data.by_account_type.map((item, i) => (
                <tr key={i} className="border-b border-border-light">
                  <td className="px-4 py-3">
                    <Badge variant="neutral">{item.account_type.replace(/_/g, " ")}</Badge>
                  </td>
                  <td className="px-4 py-3 text-text-primary">{item.count}</td>
                  <td className="px-4 py-3 font-semibold text-text-primary">{formatCurrency(item.total_balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
