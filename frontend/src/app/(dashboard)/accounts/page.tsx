"use client";

import { useEffect, useState, useCallback } from "react";
import { api, ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/Toast";
import type { AccountRead } from "@/lib/types";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<AccountRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const { toast } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.get<AccountRead[]>("/accounts");
      setAccounts(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Failed to load accounts");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSync = async (id: string) => {
    setSyncing((prev) => new Set(prev).add(id));
    try {
      await api.post(`/accounts/${id}/sync`);
      toast("Sync triggered", "success");
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Sync failed", "error");
    } finally {
      setSyncing((prev) => { const next = new Set(prev); next.delete(id); return next; });
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Disconnect "${name}"? This cannot be undone.`)) return;
    try {
      await api.del(`/accounts/${id}`);
      toast("Account disconnected", "success");
      load();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to disconnect", "error");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Accounts</h1>
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
          {error}
          <button onClick={load} className="ml-2 underline">Retry</button>
        </div>
      </div>
    );
  }

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(n);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Accounts</h1>
        <Button variant="secondary" onClick={load}>Refresh</Button>
      </div>

      {accounts.length === 0 && (
        <Card>
          <p className="text-sm text-zinc-500">No accounts connected. Connect a bank to get started.</p>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {accounts.map((acc) => (
          <Card key={acc.id}>
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium">{acc.display_name}</p>
                  <p className="text-xs text-zinc-500">{acc.account_type.replace(/_/g, " ")} · {acc.currency}</p>
                </div>
                <Badge variant={acc.is_active ? "success" : "error"}>
                  {acc.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>

              <p className="text-2xl font-bold">{formatCurrency(acc.current_balance)}</p>

              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  loading={syncing.has(acc.id)}
                  onClick={() => handleSync(acc.id)}
                >
                  Sync
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  onClick={() => handleDelete(acc.id, acc.display_name)}
                >
                  Disconnect
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
