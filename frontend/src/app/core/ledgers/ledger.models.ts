export interface Ledger {
  uuid: string;
  name: string;
  icon: string;
  color_code: string;
  last_accessed_at: number;
}

export interface LedgerPayload {
  name: string;
  icon: string;
  color_code: string;
}
