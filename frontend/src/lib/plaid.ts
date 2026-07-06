export interface PlaidLinkConfig {
  linkToken: string;
  onSuccess: (publicToken: string, metadata: PlaidSuccessMetadata) => void;
  onExit?: () => void;
}

export interface PlaidSuccessMetadata {
  institution: { institution_id: string; name: string };
  accounts: Array<{ id: string; name: string; type: string }>;
}
