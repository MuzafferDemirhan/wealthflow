"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/Toast";
import type { ConnectionRead, RequisitionRead } from "@/lib/types";

const statusVariant: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  linked: "success",
  pending: "warning",
  expired: "error",
  revoked: "error",
  error: "error",
};

const STATUS_KEY = "eb_conn_status";

export default function ConnectPage() {
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const [connections, setConnections] = useState<ConnectionRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [authorizing, setAuthorizing] = useState(false);
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

  useEffect(() => {
    const code = searchParams.get("code");
    const pending = sessionStorage.getItem(STATUS_KEY);

    if (code && pending) {
      const { id } = JSON.parse(pending);
      sessionStorage.removeItem(STATUS_KEY);
      setAuthorizing(true);

      api.post<RequisitionRead>(`/connect/requisitions/${id}/authorize`, { code })
        .then((result) => {
          if (result.status === "linked") {
            toast("Bank connected successfully!", "success");
          } else {
            toast(`Connection status: ${result.status}`, "info");
          }
        })
        .catch((e) => {
          toast(e instanceof ApiError ? e.detail : "Failed to complete connection", "error");
        })
        .finally(() => {
          setAuthorizing(false);
          load();
        });
    } else {
      load();
    }
  }, [searchParams, load, toast]);

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

  if (loading || authorizing) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <Spinner size="lg" />
        {authorizing && <p className="text-sm text-text-muted">Completing bank connection...</p>}
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Bank Connections</h1>
        <div className="rounded-lg bg-error/10 p-4 text-sm text-error">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Bank Connections</h1>
        <Link href="/connect/institutions">
          <Button>Connect a Bank</Button>
        </Link>
      </div>

      {connections.length === 0 ? (
        <Card>
          <p className="text-sm text-text-muted">No bank connections yet.</p>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {connections.map((c) => (
            <Card key={c.id}>
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-text-primary">{c.institution_name}</p>
                    <p className="text-xs text-text-muted">{c.provider}</p>
                  </div>
                  <Badge variant={statusVariant[c.status] ?? "neutral"}>{c.status}</Badge>
                </div>
                <div className="text-xs text-text-muted">
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
