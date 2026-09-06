export interface LedgerAccount {
  uuid: string;
  name: string;
  note: string | null;
  currency_uuid: string;
  icon: string;
  color_code: string;
}

export interface LedgerAccountPayload {
  name: string;
  note: string | null;
  currency_uuid: string;
  icon: string;
  color_code: string;
}

export interface LedgerCurrency {
  uuid: string;
  name: string;
  prefix: string | null;
  suffix: string | null;
  decimal_places: number;
  icon: string;
  color_code: string;
}

export interface LedgerCurrencyPayload {
  name: string;
  prefix: string | null;
  suffix: string | null;
  decimal_places: number;
  icon: string;
  color_code: string;
}
