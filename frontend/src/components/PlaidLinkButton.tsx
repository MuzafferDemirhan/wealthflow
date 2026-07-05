"use client";

import { useCallback, useEffect, useState } from "react";
import { usePlaidLink, type PlaidLinkOnSuccess } from "react-plaid-link";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";

interface PlaidLinkButtonProps {
  onSuccess: (publicToken: string, institutionId: string, institutionName: string) => Promise<void>;
}

export function PlaidLinkButton({ onSuccess }: PlaidLinkButtonProps) {
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.post<{ link_token: string }>("/connect/plaid/create-link-token")
      .then((data) => setLinkToken(data.link_token))
      .catch(() => {});
  }, []);

  const onPlaidSuccess: PlaidLinkOnSuccess = useCallback(
    (publicToken, metadata) => {
      const institutionId = metadata.institution?.institution_id ?? "";
      const institutionName = metadata.institution?.name ?? "Unknown";
      setLoading(true);
      onSuccess(publicToken, institutionId, institutionName).finally(() => setLoading(false));
    },
    [onSuccess],
  );

  const { open, ready } = usePlaidLink({
    token: linkToken,
    onSuccess: onPlaidSuccess,
  });

  return (
    <Button onClick={() => open()} disabled={!ready || !linkToken} loading={loading}>
      Connect with Plaid
    </Button>
  );
}
