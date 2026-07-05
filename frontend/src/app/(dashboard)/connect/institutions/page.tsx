"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { PlaidLinkButton } from "@/components/PlaidLinkButton";

export default function InstitutionsPage() {
  const { toast } = useToast();
  const router = useRouter();

  const handlePlaidSuccess = useCallback(
    async (publicToken: string, institutionId: string, institutionName: string) => {
      try {
        await api.post("/connect/plaid/exchange", {
          public_token: publicToken,
          institution_id: institutionId,
          institution_name: institutionName,
        });
        toast("Bank connected successfully!", "success");
        router.push("/connect");
      } catch (e) {
        toast(e instanceof ApiError ? e.detail : "Failed to complete Plaid connection", "error");
      }
    },
    [router, toast],
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight text-text-primary">Connect a Bank</h1>
      <p className="text-sm text-text-secondary">Connect your bank accounts securely via Plaid.</p>

      <Card>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-text-primary">Plaid</p>
            <p className="text-xs text-text-muted">Connect via Plaid Link SDK</p>
          </div>
          <PlaidLinkButton onSuccess={handlePlaidSuccess} />
        </div>
      </Card>
    </div>
  );
}
