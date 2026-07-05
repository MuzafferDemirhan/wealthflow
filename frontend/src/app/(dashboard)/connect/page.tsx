"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
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

  useEffect(() => {
    async function load() {
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
    }
    load();
  }, []);

  const handleDisconnect = async (id: string, institution: string) => {
    if (!window.confirm(`Disconnect from "${institution}"? Accounts from this bank will be deactivated.`)) return;
    try {
      await api.del(`/connect/connections/${id}`);
      setConnections((prev) => prev.filter((c) => c.id !== id));
      toast("Disconnected", "success");
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to disconnect", "error");
    }
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <Skeleton className="h-9 w-48" />
          <Skeleton className="h-10 w-36" />
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-outline-variant bg-surface p-6 space-y-3">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-9 w-28" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-medium tracking-tight text-on-surface">Bank Connections</h1>
        <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-medium tracking-tight text-on-surface">Bank Connections</h1>
        <Link href="/connect/institutions">
          <Button>Connect a Bank</Button>
        </Link>
      </div>

      {connections.length === 0 ? (
        <Card>
          <p className="text-sm text-on-surface-variant">No bank connections yet.</p>
        </Card>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2">
          {connections.map((c) => (
            <Card key={c.id}>
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-on-surface">{c.institution_name}</p>
                    <p className="text-xs text-on-surface-variant">{c.provider}</p>
                  </div>
                  <Badge variant={statusVariant[c.status] ?? "neutral"}>{c.status}</Badge>
                </div>
                <div className="text-xs text-on-surface-variant space-y-0.5">
                  {c.last_synced_at && <p>Last synced: {new Date(c.last_synced_at).toLocaleDateString()}</p>}
                  {c.consent_expires_at && <p>Consent expires: {new Date(c.consent_expires_at).toLocaleDateString()}</p>}
                </div>
                {c.status !== "revoked" && c.status !== "expired" && (
                  <Button size="sm" variant="danger" onClick={() => handleDisconnect(c.id, c.institution_name)}>
                    Disconnect
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
