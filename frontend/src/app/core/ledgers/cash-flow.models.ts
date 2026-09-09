export interface CashFlowPoint {
  currency_uuid: string;
  income: number;
  expense: number;
  event_count: number;
  income_movement_count: number;
  expense_movement_count: number;
}

export type CashFlowSankeySide = 'income' | 'account' | 'expense';
export type CashFlowSankeyNodeKind = 'account' | 'category';

export interface CashFlowSankeyNode {
  id: string;
  kind: CashFlowSankeyNodeKind;
  side: CashFlowSankeySide;
  label: string;
  color_code: string;
  column: number;
  order: number;
  value: number;
  category_uuid: string | null;
}

export interface CashFlowSankeyLink {
  source: string;
  target: string;
  value: number;
}

export interface CashFlowSankey {
  account_uuid: string;
  currency_uuid: string;
  from_timestamp: number;
  to_timestamp: number;
  detail_level: number;
  income: number;
  expense: number;
  nodes: CashFlowSankeyNode[];
  links: CashFlowSankeyLink[];
}
