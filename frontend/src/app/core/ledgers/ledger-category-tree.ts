import { LedgerCategory, LedgerCategoryTreeNode } from './ledger-categories.models';

export function flattenCategoryTree(nodes: readonly LedgerCategoryTreeNode[]): LedgerCategory[] {
  const categories: LedgerCategory[] = [];
  const visit = (items: readonly LedgerCategoryTreeNode[]) => {
    for (const node of items) {
      categories.push(node.category);
      visit(node.children);
    }
  };
  visit(nodes);
  return categories;
}

export function categoryPathMap(nodes: readonly LedgerCategoryTreeNode[]): ReadonlyMap<string, string> {
  const paths = new Map<string, string>();
  const visit = (items: readonly LedgerCategoryTreeNode[], ancestors: readonly string[]) => {
    for (const node of items) {
      const parts = [...ancestors, node.category.name];
      paths.set(node.category.uuid, parts.join(' › '));
      visit(node.children, parts);
    }
  };
  visit(nodes, []);
  return paths;
}

export function categoryPath(category: LedgerCategory, byUuid: ReadonlyMap<string, LedgerCategory>): string {
  const names: string[] = [];
  const seen = new Set<string>();
  let current: LedgerCategory | undefined = category;
  while (current && !seen.has(current.uuid)) {
    seen.add(current.uuid);
    names.unshift(current.name);
    current = current.parent_uuid ? byUuid.get(current.parent_uuid) : undefined;
  }
  return names.join(' › ');
}
