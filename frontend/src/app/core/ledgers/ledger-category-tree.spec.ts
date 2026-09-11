import { describe, expect, it } from 'vitest';
import { categoryPath, categoryPathMap, flattenCategoryTree } from './ledger-category-tree';
import { LedgerCategory, LedgerCategoryTreeNode } from './ledger-categories.models';

const root: LedgerCategory = { uuid: 'root', name: 'Casa', icon: 'lucide:home', color_code: '#000000', parent_uuid: null };
const child: LedgerCategory = { uuid: 'child', name: 'Mercado', icon: 'lucide:shopping-cart', color_code: '#000000', parent_uuid: 'root' };
const tree: LedgerCategoryTreeNode[] = [{ category: root, children: [{ category: child, children: [] }] }];

describe('ledger category tree helpers', () => {
  it('flattens preorder and builds stable paths', () => {
    expect(flattenCategoryTree(tree)).toEqual([root, child]);
    expect(categoryPathMap(tree).get('child')).toBe('Casa › Mercado');
    expect(categoryPath(child, new Map([['root', root], ['child', child]]))).toBe('Casa › Mercado');
  });
});
