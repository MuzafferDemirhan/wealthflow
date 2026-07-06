"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import type { BudgetRead, CategoryRead, BudgetCreate, BudgetUpdate } from "@/lib/types";

export default function BudgetsPage() {
  const { toast } = useToast();
  const [budgets, setBudgets] = useState<BudgetRead[]>([]);
  const [categories, setCategories] = useState<CategoryRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ category_id: "", period_month: "", amount_limit: "", currency: "PLN" });
  const [creating, setCreating] = useState(false);

  const [editing, setEditing] = useState<BudgetRead | null>(null);
  const [editForm, setEditForm] = useState({ amount_limit: "", category_id: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [b, c] = await Promise.all([
          api.get<BudgetRead[]>("/budgets"),
          api.get<CategoryRead[]>("/categories"),
        ]);
        setBudgets(b);
        setCategories(c);
      } catch (e) {
        setError(e instanceof ApiError ? e.detail : "Failed to load budgets");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const refresh = async () => {
    try {
      const [b, c] = await Promise.all([
        api.get<BudgetRead[]>("/budgets"),
        api.get<CategoryRead[]>("/categories"),
      ]);
      setBudgets(b);
      setCategories(c);
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to refresh budgets", "error");
    }
  };

  const handleCreate = async () => {
    if (!createForm.amount_limit || !createForm.period_month) {
      toast("Amount and month are required", "error");
      return;
    }
    setCreating(true);
    try {
      const body: BudgetCreate = {
        amount_limit: parseFloat(createForm.amount_limit),
        period_month: createForm.period_month,
        currency: createForm.currency,
        category_id: createForm.category_id || undefined,
      };
      await api.post("/budgets", body);
      toast("Budget created", "success");
      setShowCreate(false);
      setCreateForm({ category_id: "", period_month: "", amount_limit: "", currency: "PLN" });
      refresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to create budget", "error");
    } finally {
      setCreating(false);
    }
  };

  const handleEdit = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      const body: BudgetUpdate = {};
      if (editForm.amount_limit) body.amount_limit = parseFloat(editForm.amount_limit);
      if (editForm.category_id) body.category_id = editForm.category_id;
      await api.put(`/budgets/${editing.id}`, body);
      toast("Budget updated", "success");
      setEditing(null);
      refresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to update budget", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (budget: BudgetRead) => {
    if (!window.confirm(`Delete this budget?`)) return;
    try {
      await api.del(`/budgets/${budget.id}`);
      toast("Budget deleted", "success");
      refresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to delete budget", "error");
    }
  };

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  const catOpts = categories.map((c) => ({ value: c.id, label: c.name }));

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <Skeleton className="h-9 w-36" />
          <Skeleton className="h-10 w-36" />
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-outline-variant bg-surface p-6 space-y-4">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-2 w-full" />
              <Skeleton className="h-4 w-24" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-medium tracking-tight text-on-surface">Budgets</h1>
        <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-medium tracking-tight text-on-surface">Budgets</h1>
        <Button onClick={() => setShowCreate(true)}>Create Budget</Button>
      </div>

      {budgets.length === 0 && (
        <Card>
          <p className="text-sm text-on-surface-variant">No budgets yet. Create one to start tracking your spending.</p>
        </Card>
      )}

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {budgets.map((b) => {
          const cat = categories.find((c) => c.id === b.category_id);
          const progressColor =
            b.progress_pct >= 100 ? "bg-error" : b.progress_pct >= 80 ? "bg-warning" : "bg-success";

          return (
            <Card key={b.id}>
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-on-surface">{cat?.name ?? "Uncategorized"}</p>
                    <p className="text-xs text-on-surface-variant">{b.period_month}</p>
                  </div>
                  <div className="flex gap-1">
                    <Button size="sm" variant="ghost" onClick={() => { setEditing(b); setEditForm({ amount_limit: String(b.amount_limit), category_id: b.category_id ?? "" }); }}>
                      Edit
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => handleDelete(b)}>
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </Button>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm">
                    <span className="text-on-surface">{formatCurrency(b.spent)}</span>
                    <span className="text-on-surface-variant">of {formatCurrency(b.amount_limit)}</span>
                  </div>
                  <div className="mt-2 h-2.5 w-full rounded-full bg-surface-container-high">
                    <div
                      className={`h-2.5 rounded-full transition-all ${progressColor}`}
                      style={{ width: `${Math.min(b.progress_pct, 100)}%` }}
                    />
                  </div>
                  <div className="mt-2 flex justify-between text-xs text-on-surface-variant">
                    <span>{b.progress_pct.toFixed(0)}% used</span>
                    <span>{formatCurrency(b.remaining)} remaining</span>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Budget">
        <div className="space-y-4">
          <Select label="Category" options={catOpts} placeholder="All categories" value={createForm.category_id} onChange={(e) => setCreateForm((f) => ({ ...f, category_id: e.target.value }))} />
          <Input label="Month" type="month" value={createForm.period_month} onChange={(e) => setCreateForm((f) => ({ ...f, period_month: e.target.value }))} required />
          <Input label="Amount Limit" type="number" step="0.01" value={createForm.amount_limit} onChange={(e) => setCreateForm((f) => ({ ...f, amount_limit: e.target.value }))} required />
          <Input label="Currency" value={createForm.currency} onChange={(e) => setCreateForm((f) => ({ ...f, currency: e.target.value }))} />
          <Button onClick={handleCreate} loading={creating} className="w-full">Create</Button>
        </div>
      </Modal>

      {/* Edit Modal */}
      <Modal open={!!editing} onClose={() => setEditing(null)} title="Edit Budget">
        <div className="space-y-4">
          <Input label="Amount Limit" type="number" step="0.01" value={editForm.amount_limit} onChange={(e) => setEditForm((f) => ({ ...f, amount_limit: e.target.value }))} />
          <Select label="Category" options={catOpts} placeholder="Keep current" value={editForm.category_id} onChange={(e) => setEditForm((f) => ({ ...f, category_id: e.target.value }))} />
          <Button onClick={handleEdit} loading={saving} className="w-full">Save</Button>
        </div>
      </Modal>
    </div>
  );
}
