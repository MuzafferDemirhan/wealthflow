"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
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
    <div className="space-y-8">
      <div>
        <Link
          href="/connect"
          className="inline-flex items-center gap-1.5 text-sm text-on-surface-variant hover:text-on-surface transition-colors mb-4"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Bank Connections
        </Link>
        <h1 className="text-3xl font-medium tracking-tight text-on-surface">Connect a Bank</h1>
        <p className="text-sm text-on-surface-variant">Connect your bank accounts securely via Plaid.</p>
      </div>

      <Card>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-on-surface">Plaid</p>
            <p className="text-xs text-on-surface-variant">Connect via Plaid Link SDK</p>
          </div>
          <PlaidLinkButton onSuccess={handlePlaidSuccess} />
        </div>
      </Card>
    </div>
  );
}
