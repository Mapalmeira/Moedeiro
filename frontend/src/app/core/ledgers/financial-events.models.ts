export const MAX_SHOPPING_LIST_MOVEMENTS = 300;

export type FinancialEventType = 'TRANSACTION' | 'ACCOUNT_TRANSFER' | 'SHOPPING_LIST';

export interface FinancialMovement {
  uuid: string;
  account_uuid: string;
  category_uuid: string;
  value: number;
  quantity: number;
  item_name: string | null;
}

export interface FinancialEvent {
  uuid: string;
  occurred_at: number;
  description: string;
  type: FinancialEventType;
  movements: FinancialMovement[];
}

export interface FinancialEventPage {
  events: FinancialEvent[];
  next_cursor: string | null;
}

export interface FinancialEventFilters {
  from_timestamp: number;
  to_timestamp: number;
  page_size: number;
  account_uuid?: string | null;
  category_uuid?: string | null;
  event_type?: FinancialEventType | null;
  cursor?: string | null;
  ascending?: boolean;
}

export interface SimpleFinancialEventPayload {
  type: 'TRANSACTION';
  occurred_at: number;
  description: string;
  account_uuid: string;
  category_uuid: string;
  value: number;
  quantity: number;
  item_name: string | null;
}

export interface ShoppingListMovementPayload {
  uuid?: string | null;
  category_uuid: string;
  value: number;
  quantity: number;
  item_name: string | null;
}

export interface ShoppingListFinancialEventPayload {
  type: 'SHOPPING_LIST';
  occurred_at: number;
  description: string;
  account_uuid: string;
  movements: ShoppingListMovementPayload[];
}

export interface AccountTransferFinancialEventPayload {
  type: 'ACCOUNT_TRANSFER';
  occurred_at: number;
  description: string;
  source_account_uuid: string;
  source_category_uuid: string;
  source_value: number;
  destination_account_uuid: string;
  destination_category_uuid: string;
  destination_value: number;
  fee: { category_uuid: string; value: number } | null;
}

export type CreateFinancialEventPayload =
  | SimpleFinancialEventPayload
  | Omit<ShoppingListFinancialEventPayload, 'movements'> & { movements: Array<Omit<ShoppingListMovementPayload, 'uuid'>> }
  | AccountTransferFinancialEventPayload;

export type UpdateFinancialEventPayload =
  | SimpleFinancialEventPayload
  | ShoppingListFinancialEventPayload
  | AccountTransferFinancialEventPayload;
