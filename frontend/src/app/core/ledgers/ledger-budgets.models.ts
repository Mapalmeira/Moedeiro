export type LedgerBudgetState = 'FUTURE' | 'ACTIVE' | 'FINISHED';

export interface LedgerBudget {
  uuid: string;
  account_uuid: string;
  category_uuid: string;
  from_timestamp: number;
  to_timestamp: number;
  name: string;
  description: string | null;
  amount: number;
}

export interface LedgerBudgetOverview extends LedgerBudget {
  state: LedgerBudgetState;
  spent_amount: number | null;
  fulfilled: boolean | null;
}

export interface LedgerBudgetOverviewPage {
  items: LedgerBudgetOverview[];
  next_cursor: string | null;
}

export interface CreateLedgerBudgetPayload {
  account_uuid: string;
  category_uuid: string;
  from_timestamp: number;
  to_timestamp: number;
  name: string;
  description: string | null;
  amount: number;
}

export interface UpdateLedgerBudgetPayload extends Omit<CreateLedgerBudgetPayload, 'account_uuid'> {}
