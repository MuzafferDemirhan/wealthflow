"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/Toast";
import type { InstitutionRead, RequisitionCreateResponse } from "@/lib/types";

const STATUS_KEY = "eb_conn_status";

const COUNTRIES = [
  { code: "PL", name: "Poland" },
  { code: "TR", name: "Turkey" },
  { code: "GB", name: "United Kingdom" },
  { code: "DE", name: "Germany" },
  { code: "FR", name: "France" },
  { code: "ES", name: "Spain" },
  { code: "IT", name: "Italy" },
  { code: "NL", name: "Netherlands" },
  { code: "BE", name: "Belgium" },
  { code: "PT", name: "Portugal" },
  { code: "SE", name: "Sweden" },
  { code: "NO", name: "Norway" },
  { code: "DK", name: "Denmark" },
  { code: "FI", name: "Finland" },
  { code: "IE", name: "Ireland" },
  { code: "AT", name: "Austria" },
  { code: "RO", name: "Romania" },
  { code: "BG", name: "Bulgaria" },
  { code: "GR", name: "Greece" },
  { code: "CZ", name: "Czech Republic" },
  { code: "HU", name: "Hungary" },
  { code: "SK", name: "Slovakia" },
  { code: "SI", name: "Slovenia" },
  { code: "HR", name: "Croatia" },
  { code: "LT", name: "Lithuania" },
  { code: "LV", name: "Latvia" },
  { code: "EE", name: "Estonia" },
  { code: "CY", name: "Cyprus" },
  { code: "LU", name: "Luxembourg" },
  { code: "MT", name: "Malta" },
];

export default function InstitutionsPage() {
  const { toast } = useToast();
  const [country, setCountry] = useState("TR");
  const [institutions, setInstitutions] = useState<InstitutionRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    api.get<InstitutionRead[]>("/connect/institutions", { country })
      .then(setInstitutions)
      .catch((e) => setError(e.detail ?? "Failed to load institutions"))
      .finally(() => setLoading(false));
  }, [country]);

  const handleConnect = async (institutionId: string) => {
    setConnecting(institutionId);
    try {
      const redirectUri = `${window.location.origin}/connect`;
      const result = await api.post<RequisitionCreateResponse>("/connect/requisitions", {
        institution_id: institutionId,
        redirect_uri: redirectUri,
      });
      sessionStorage.setItem(STATUS_KEY, JSON.stringify({ id: result.id, state: result.state }));
      window.location.href = result.link;
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "Failed to initiate connection", "error");
      setConnecting(null);
    }
  };

  if (loading) return <div className="flex justify-center py-24"><Spinner size="lg" /></div>;

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Connect a Bank</h1>
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Connect a Bank</h1>
      <p className="text-sm text-zinc-500">Select your country and bank to connect via Open Banking (PSD2).</p>

      <div className="flex items-center gap-2">
        <label className="text-sm font-medium text-zinc-700">Country:</label>
        <select
          className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm"
          value={country}
          onChange={(e) => setCountry(e.target.value)}
        >
          {COUNTRIES.map((c) => (
            <option key={c.code} value={c.code}>{c.name}</option>
          ))}
        </select>
      </div>

      {institutions.length === 0 ? (
        <Card>
          <p className="text-sm text-zinc-500">No institutions available for your region.</p>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {institutions.map((inst) => (
            <Card key={inst.id}>
              <div className="flex items-center gap-4">
                {inst.logo && (
                  <img
                    src={inst.logo}
                    alt={inst.name}
                    className="h-10 w-10 rounded-lg object-contain"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                )}
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{inst.name}</p>
                  <p className="text-xs text-zinc-500">{inst.country}</p>
                </div>
                <Button
                  size="sm"
                  loading={connecting === inst.id}
                  onClick={() => handleConnect(inst.id)}
                >
                  Connect
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
