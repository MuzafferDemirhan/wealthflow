"use client";

import { useCallback, useEffect, useState } from "react";
import { usePlaidLink } from "react-plaid-link";
import { api, ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";

interface Props {
  onSuccess: (publicToken: string, institutionId: string, institutionName: string) => void;
  onError?: (error: string) => void;
}

export function PlaidLinkButton({ onSuccess, onError }: Props) {
  const { toast } = useToast();
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .post<{ link_token: string }>("/connect/plaid/link-token", {})
      .then((res) => setLinkToken(res.link_token))
      .catch(() => {
        const msg = "Failed to initialize bank connection";
        onError?.(msg);
        toast(msg, "error");
      })
      .finally(() => setLoading(false));
  }, [onError, toast]);

  const handleOnSuccess = useCallback(
    (publicToken: string, metadata: { institution?: { institution_id?: string; name?: string } | null }) => {
      const inst = metadata.institution;
      onSuccess(publicToken, inst?.institution_id ?? "", inst?.name ?? "Unknown");
    },
    [onSuccess],
  );

  const { open, ready } = usePlaidLink({
    token: linkToken ?? "",
    onSuccess: handleOnSuccess,
    onExit: (err) => {
      if (err) {
        const msg = "Connection cancelled or failed";
        onError?.(msg);
        toast(msg, "error");
      }
    },
  });

  return (
    <Button
      onClick={() => open()}
      loading={loading}
      disabled={!ready || !linkToken}
    >
      Connect with Plaid
    </Button>
  );
}
