"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import type {
  AccountRead,
  ReportNetWorth,
  ReportIncomeVsExpenses,
  TransactionRead,
} from "@/lib/types";

// ──────────────────────────────────────────────
// Section Loader
// ──────────────────────────────────────────────

function SectionLoader() {
  return (
    <div className="flex items-center justify-center py-12">
      <Spinner />
    </div>
  );
}

function SectionError({ message }: { message: string }) {
  return (
    <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
      {message}
    </div>
  );
}

// ──────────────────────────────────────────────
// Net Worth Card
// ──────────────────────────────────────────────

function NetWorthCard() {
  const [data, setData] = useState<ReportNetWorth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<ReportNetWorth>("/reports/net-worth")
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load net worth"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <SectionLoader />;
  if (error) return <SectionError message={error} />;
  if (!data) return null;

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(n);

  return (
    <Card title="Net Worth">
      <div className="grid grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-zinc-500">Assets</p>
          <p className="text-lg font-semibold text-emerald-600">{formatCurrency(data.total_assets)}</p>
        </div>
        <div>
          <p className="text-xs text-zinc-500">Liabilities</p>
          <p className="text-lg font-semibold text-red-600">{formatCurrency(data.total_liabilities)}</p>
        </div>
        <div>
          <p className="text-xs text-zinc-500">Net Worth</p>
          <p className="text-lg font-semibold">{formatCurrency(data.net_worth)}</p>
        </div>
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────
// Income vs Expenses Chart
// ──────────────────────────────────────────────

function IncomeExpensesChart() {
  const [data, setData] = useState<ReportIncomeVsExpenses | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const now = new Date();
    const from = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split("T")[0];
    const to = now.toISOString().split("T")[0];

    api.get<ReportIncomeVsExpenses>("/reports/income-vs-expenses", { date_from: from, date_to: to, monthly: "true" })
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load income vs expenses"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <SectionLoader />;
  if (error) return <SectionError message={error} />;
  if (!data) return null;

  const chartData = data.monthly_breakdown?.length
    ? data.monthly_breakdown.map((m) => ({
        month: m.month.slice(0, 7),
        Income: m.income,
        Expenses: m.expenses,
      }))
    : [{ month: "Current", Income: data.total_income, Expenses: data.total_expenses }];

  return (
    <Card title="Income vs Expenses">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="Income" fill="#059669" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Expenses" fill="#dc2626" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────
// Account Summary
// ──────────────────────────────────────────────

function AccountSummary() {
  const [data, setData] = useState<AccountRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<AccountRead[]>("/accounts")
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load accounts"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <SectionLoader />;
  if (error) return <SectionError message={error} />;

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(n);

  if (data.length === 0) {
    return (
      <Card title="Accounts">
        <p className="text-sm text-zinc-500">No accounts connected yet.</p>
      </Card>
    );
  }

  return (
    <Card title="Accounts">
      <div className="space-y-3">
        {data.slice(0, 4).map((acc) => (
          <div key={acc.id} className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{acc.display_name}</p>
              <p className="text-xs text-zinc-500">{acc.account_type.replace("_", " ")}</p>
            </div>
            <p className="text-sm font-semibold">{formatCurrency(acc.current_balance)}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────
// Recent Transactions
// ──────────────────────────────────────────────

const statusVariant = {
  booked: "success" as const,
  pending: "warning" as const,
};

function RecentTransactions() {
  const [data, setData] = useState<TransactionRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<TransactionRead[]>("/transactions", { limit: 5 })
      .then(setData)
      .catch((e) => setError(e.detail ?? "Failed to load transactions"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <SectionLoader />;
  if (error) return <SectionError message={error} />;

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(n);

  if (data.length === 0) {
    return (
      <Card title="Recent Transactions">
        <p className="text-sm text-zinc-500">No transactions yet.</p>
      </Card>
    );
  }

  const totalCount = data.length;

  return (
    <Card title={`Recent Transactions (${totalCount})`}>
      <div className="space-y-2">
        {data.map((tx) => (
          <div key={tx.id} className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{tx.description || "No description"}</p>
              <p className="text-xs text-zinc-500">{tx.booking_date}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold ${tx.amount < 0 ? "text-red-600" : "text-emerald-600"}`}>
                {formatCurrency(Math.abs(tx.amount))}
              </span>
              <Badge variant={statusVariant[tx.status] ?? "neutral"}>{tx.status}</Badge>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────
// Dashboard Page
// ──────────────────────────────────────────────

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>

      <div className="grid gap-6 sm:grid-cols-2">
        <NetWorthCard />
        <AccountSummary />
      </div>

      <IncomeExpensesChart />

      <RecentTransactions />
    </div>
  );
}
