export interface LedgerCategory {
  uuid: string;
  name: string;
  icon: string;
  color_code: string;
  parent_uuid: string | null;
}

export interface LedgerCategoryTreeNode {
  category: LedgerCategory;
  children: LedgerCategoryTreeNode[];
}

export interface LedgerCategoryPayload {
  name: string;
  icon: string;
  color_code: string;
  parent_uuid: string | null;
}
