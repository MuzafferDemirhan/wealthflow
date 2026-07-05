"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
import { useToast } from "@/components/ui/Toast";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import type { HoldingRead, PortfolioSummary, HoldingCreate, AssetType } from "@/lib/types";

const COLORS = ["#005bbf", "#34a853", "#fbbc04", "#ba1a1a", "#8B5CF6", "#06B6D4", "#EC4899"];

const assetTypeLabels: Record<string, string> = {
  stock: "Stocks", etf: "ETFs", mutual_fund: "Mutual Funds",
  bond: "Bonds", crypto: "Crypto", cash: "Cash", other: "Other",
};

const assetTypeOpts = Object.entries(assetTypeLabels).map(([value, label]) => ({ value, label }));

export default function PortfolioPage() {
  const { toast } = useToast();
  const [holdings, setHoldings] = useState<HoldingRead[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState<HoldingCreate>({
    symbol: "", name: "", asset_type: "stock" as AssetType, currency: "PLN",
    quantity: 0, cost_basis: undefined, current_price: undefined,
  });
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [h, s] = await Promise.all([
          api.get<HoldingRead[]>("/portfolio/holdings"),
          api.get<PortfolioSummary>("/portfolio/summary"),
        ]);
        setHoldings(h);
        setSummary(s);
      } catch (e) {
        setError(e instanceof ApiError ? e.detail : "Failed to load portfolio");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const refresh = async () => {
    try {
      const [h, s] = await Promise.all([
        api.get<HoldingRead[]>("/portfolio/holdings"),
        api.get<PortfolioSummary>("/portfolio/summary"),
      ]);
      setHoldings(h);
      setSummary(s);
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to refresh portfolio", "error");
    }
  };

  const handleAdd = async () => {
    if (!addForm.symbol || !addForm.name || addForm.quantity <= 0) {
      toast("Symbol, name, and quantity are required", "error");
      return;
    }
    setAdding(true);
    try {
      await api.post("/portfolio/holdings", addForm);
      toast("Holding added", "success");
      setShowAdd(false);
      setAddForm({ symbol: "", name: "", asset_type: "stock" as AssetType, currency: "PLN", quantity: 0 });
      refresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to add holding", "error");
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Remove "${name}"?`)) return;
    try {
      await api.del(`/portfolio/holdings/${id}`);
      toast("Holding removed", "success");
      refresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to remove holding", "error");
    }
  };

  const formatCurrency = (n: number | null | undefined) =>
    n != null ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n) : "-";

  const allocationData = summary
    ? Object.entries(summary.allocation).map(([name, value]) => ({
        name: assetTypeLabels[name] ?? name,
        value,
      }))
    : [];

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <Skeleton className="h-9 w-40" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-5 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-outline-variant bg-surface p-6 space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-7 w-28" />
            </div>
          ))}
        </div>
        <div className="rounded-xl border border-outline-variant bg-surface p-6">
          <Skeleton className="h-4 w-24 mb-4" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-medium tracking-tight text-on-surface">Portfolio</h1>
        <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-medium tracking-tight text-on-surface">Portfolio</h1>
        <Button onClick={() => setShowAdd(true)}>Add Holding</Button>
      </div>

      {/* Summary */}
      {summary && (
        <div className="grid gap-5 sm:grid-cols-4">
          <Card>
            <p className="text-xs text-on-surface-variant">Market Value</p>
            <p className="text-2xl font-semibold text-on-surface">{formatCurrency(summary.total_market_value)}</p>
          </Card>
          <Card>
            <p className="text-xs text-on-surface-variant">Cost Basis</p>
            <p className="text-2xl font-semibold text-on-surface">{formatCurrency(summary.total_cost_basis)}</p>
          </Card>
          <Card>
            <p className="text-xs text-on-surface-variant">Gain / Loss</p>
            <p className={`text-2xl font-semibold ${(summary.total_gain_loss ?? 0) >= 0 ? "text-success" : "text-error"}`}>
              {formatCurrency(summary.total_gain_loss)}
              {summary.total_gain_loss_pct != null && (
                <span className="ml-1 text-sm font-normal">({(summary.total_gain_loss_pct >= 0 ? "+" : "")}{summary.total_gain_loss_pct.toFixed(1)}%)</span>
              )}
            </p>
          </Card>
          <Card>
            <p className="text-xs text-on-surface-variant">Holdings</p>
            <p className="text-2xl font-semibold text-on-surface">{summary.holdings_count}</p>
          </Card>
        </div>
      )}

      {/* Allocation Chart */}
      {allocationData.length > 0 && (
        <Card title="Allocation">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={allocationData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={{ fill: 'var(--color-on-surface-variant)', fontSize: 12 }}>
                  {allocationData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<ChartTooltip formatter={(v) => formatCurrency(v)} />} />
                <Legend wrapperStyle={{ color: 'var(--color-on-surface-variant)' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Holdings Table */}
      <Card title="Holdings">
        {holdings.length === 0 ? (
          <p className="text-sm text-on-surface-variant">No holdings yet. Add your first investment.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr>
                  <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Symbol</th>
                  <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Name</th>
                  <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Type</th>
                  <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Qty</th>
                  <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Avg Cost</th>
                  <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Price</th>
                  <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Market Value</th>
                  <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant"></th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => (
                  <tr key={h.id} className="border-t border-outline-variant/50">
                    <td className="py-3 pr-4 font-medium text-on-surface">{h.symbol}</td>
                    <td className="py-3 pr-4 text-on-surface">{h.name}</td>
                    <td className="py-3 pr-4"><Badge variant="neutral">{assetTypeLabels[h.asset_type] ?? h.asset_type}</Badge></td>
                    <td className="py-3 pr-4 text-on-surface">{h.quantity}</td>
                    <td className="py-3 pr-4 text-on-surface">{formatCurrency(h.cost_basis)}</td>
                    <td className="py-3 pr-4 text-on-surface">{formatCurrency(h.current_price)}</td>
                    <td className="py-3 pr-4 font-semibold text-on-surface">{formatCurrency(h.market_value)}</td>
                    <td className="py-3">
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(h.id, h.symbol)}>
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Add Holding Modal */}
      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Holding">
        <div className="space-y-4">
          <Input label="Symbol" value={addForm.symbol} onChange={(e) => setAddForm((f) => ({ ...f, symbol: e.target.value }))} placeholder="AAPL" required />
          <Input label="Name" value={addForm.name} onChange={(e) => setAddForm((f) => ({ ...f, name: e.target.value }))} placeholder="Apple Inc." required />
          <Select label="Type" options={assetTypeOpts} value={addForm.asset_type} onChange={(e) => setAddForm((f) => ({ ...f, asset_type: e.target.value as AssetType }))} />
          <Input label="Currency" value={addForm.currency} onChange={(e) => setAddForm((f) => ({ ...f, currency: e.target.value }))} />
          <Input label="Quantity" type="number" step="0.000001" value={addForm.quantity || ""} onChange={(e) => setAddForm((f) => ({ ...f, quantity: parseFloat(e.target.value) || 0 }))} required />
          <Input label="Cost Basis (per share)" type="number" step="0.01" value={addForm.cost_basis || ""} onChange={(e) => setAddForm((f) => ({ ...f, cost_basis: e.target.value ? parseFloat(e.target.value) : undefined }))} />
          <Input label="Current Price" type="number" step="0.01" value={addForm.current_price || ""} onChange={(e) => setAddForm((f) => ({ ...f, current_price: e.target.value ? parseFloat(e.target.value) : undefined }))} />
          <Button onClick={handleAdd} loading={adding} className="w-full">Add Holding</Button>
        </div>
      </Modal>
    </div>
  );
}
