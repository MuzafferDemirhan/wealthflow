"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/Toast";
import type { ConnectionRead } from "@/lib/types";

const statusVariant: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  linked: "success",
  pending: "warning",
  expired: "error",
  revoked: "error",
  error: "error",
};

export default function ConnectPage() {
  const { toast } = useToast();
  const [connections, setConnections] = useState<ConnectionRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.get<ConnectionRead[]>("/connect/connections");
      setConnections(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Failed to load connections");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDisconnect = async (id: string, institution: string) => {
    if (!window.confirm(`Disconnect from "${institution}"? Accounts from this bank will be deactivated.`)) return;
    try {
      await api.del(`/connect/connections/${id}`);
      toast("Disconnected", "success");
      load();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to disconnect", "error");
    }
  };

  if (loading) return <div className="flex justify-center py-24"><Spinner size="lg" /></div>;

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Bank Connections</h1>
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Bank Connections</h1>
        <Link href="/connect/institutions">
          <Button>Connect a Bank</Button>
        </Link>
      </div>

      {connections.length === 0 ? (
        <Card>
          <p className="text-sm text-zinc-500">No bank connections yet.</p>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {connections.map((c) => (
            <Card key={c.id}>
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{c.institution_name}</p>
                    <p className="text-xs text-zinc-500">{c.provider} · {c.institution_id}</p>
                  </div>
                  <Badge variant={statusVariant[c.status] ?? "neutral"}>{c.status}</Badge>
                </div>
                <div className="text-xs text-zinc-500">
                  {c.last_synced_at && <p>Last synced: {new Date(c.last_synced_at).toLocaleDateString()}</p>}
                  {c.consent_expires_at && <p>Consent expires: {new Date(c.consent_expires_at).toLocaleDateString()}</p>}
                </div>
                <Button size="sm" variant="danger" onClick={() => handleDisconnect(c.id, c.institution_name)}>
                  Disconnect
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
