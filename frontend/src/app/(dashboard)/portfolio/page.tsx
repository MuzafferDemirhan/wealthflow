"use client";

import { useEffect, useState, useCallback } from "react";
import { api, ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/Toast";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import type { HoldingRead, PortfolioSummary, HoldingCreate, AssetType } from "@/lib/types";

const COLORS = ["#059669", "#2563eb", "#d97706", "#dc2626", "#7c3aed", "#0891b2", "#be123c"];

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

  // Add modal
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState<HoldingCreate>({
    symbol: "", name: "", asset_type: "stock" as AssetType, currency: "PLN",
    quantity: 0, cost_basis: undefined, current_price: undefined,
  });
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
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
  }, []);

  useEffect(() => { load(); }, [load]);

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
      load();
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
      load();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to remove holding", "error");
    }
  };

  const formatCurrency = (n: number | null | undefined) =>
    n != null ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n) : "—";

  const allocationData = summary
    ? Object.entries(summary.allocation).map(([name, value]) => ({
        name: assetTypeLabels[name] ?? name,
        value,
      }))
    : [];

  if (loading) return <div className="flex items-center justify-center py-24"><Spinner size="lg" /></div>;

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Portfolio</h1>
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Portfolio</h1>
        <Button onClick={() => setShowAdd(true)}>Add Holding</Button>
      </div>

      {/* Summary */}
      {summary && (
        <div className="grid gap-4 sm:grid-cols-4">
          <Card>
            <p className="text-xs text-zinc-500">Market Value</p>
            <p className="text-xl font-bold">{formatCurrency(summary.total_market_value)}</p>
          </Card>
          <Card>
            <p className="text-xs text-zinc-500">Cost Basis</p>
            <p className="text-xl font-bold">{formatCurrency(summary.total_cost_basis)}</p>
          </Card>
          <Card>
            <p className="text-xs text-zinc-500">Gain / Loss</p>
            <p className={`text-xl font-bold ${(summary.total_gain_loss ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"}`}>
              {formatCurrency(summary.total_gain_loss)}
              {summary.total_gain_loss_pct != null && (
                <span className="ml-1 text-sm">({(summary.total_gain_loss_pct >= 0 ? "+" : "")}{summary.total_gain_loss_pct.toFixed(1)}%)</span>
              )}
            </p>
          </Card>
          <Card>
            <p className="text-xs text-zinc-500">Holdings</p>
            <p className="text-xl font-bold">{summary.holdings_count}</p>
          </Card>
        </div>
      )}

      {/* Allocation Chart */}
      {allocationData.length > 0 && (
        <Card title="Allocation">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={allocationData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {allocationData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Holdings Table */}
      <Card title="Holdings">
        {holdings.length === 0 ? (
          <p className="text-sm text-zinc-500">No holdings yet. Add your first investment.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800">
                  <th className="px-4 py-3 font-medium text-zinc-500">Symbol</th>
                  <th className="px-4 py-3 font-medium text-zinc-500">Name</th>
                  <th className="px-4 py-3 font-medium text-zinc-500">Type</th>
                  <th className="px-4 py-3 font-medium text-zinc-500">Qty</th>
                  <th className="px-4 py-3 font-medium text-zinc-500">Avg Cost</th>
                  <th className="px-4 py-3 font-medium text-zinc-500">Price</th>
                  <th className="px-4 py-3 font-medium text-zinc-500">Market Value</th>
                  <th className="px-4 py-3 font-medium text-zinc-500"></th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => {
                  const gainLoss = h.market_value != null && h.cost_basis != null
                    ? h.market_value - h.cost_basis * h.quantity
                    : null;
                  return (
                    <tr key={h.id} className="border-b border-zinc-100 dark:border-zinc-800/50">
                      <td className="px-4 py-3 font-medium">{h.symbol}</td>
                      <td className="px-4 py-3">{h.name}</td>
                      <td className="px-4 py-3"><Badge>{assetTypeLabels[h.asset_type] ?? h.asset_type}</Badge></td>
                      <td className="px-4 py-3">{h.quantity}</td>
                      <td className="px-4 py-3">{formatCurrency(h.cost_basis)}</td>
                      <td className="px-4 py-3">{formatCurrency(h.current_price)}</td>
                      <td className="px-4 py-3 font-semibold">{formatCurrency(h.market_value)}</td>
                      <td className="px-4 py-3">
                        <Button size="sm" variant="ghost" onClick={() => handleDelete(h.id, h.symbol)}>✕</Button>
                      </td>
                    </tr>
                  );
                })}
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
