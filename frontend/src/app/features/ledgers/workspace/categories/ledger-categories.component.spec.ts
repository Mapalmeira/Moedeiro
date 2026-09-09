import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerCategory, LedgerCategoryTreeNode } from '../../../../core/ledgers/ledger-categories.models';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { LedgerWorkspaceStateService } from '../../../../core/ledgers/ledger-workspace-state.service';
import { LedgerCategoriesComponent } from './ledger-categories.component';

const food: LedgerCategory = { uuid: 'food', name: 'Alimentação', icon: 'lucide:Utensils', color_code: '#21E683', parent_uuid: null };
const restaurants: LedgerCategory = { uuid: 'restaurants', name: 'Restaurantes', icon: 'lucide:Soup', color_code: '#FFD51A', parent_uuid: food.uuid };
const transport: LedgerCategory = { uuid: 'transport', name: 'Transporte', icon: 'lucide:Car', color_code: '#488DFC', parent_uuid: null };
const tree: LedgerCategoryTreeNode[] = [
  { category: food, children: [{ category: restaurants, children: [] }] },
  { category: transport, children: [] },
];

describe('LedgerCategoriesComponent', () => {
  const ledgerUuid = signal('ledger');
  const categoriesService = {
    getTree: vi.fn(() => of(tree)),
    update: vi.fn((_ledgerUuid: string, _categoryUuid: string, payload: LedgerCategory) => of(payload)),
    delete: vi.fn(() => of(void 0)),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    ledgerUuid.set('ledger');
    categoriesService.getTree.mockReturnValue(of(tree));
    TestBed.configureTestingModule({
      providers: [
        LedgerWorkspaceStateService,
        { provide: LedgerCategoriesService, useValue: categoriesService },
        { provide: LedgerContextService, useValue: { ledgerUuid: ledgerUuid.asReadonly() } },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'error') } },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
  });

  function createComponent(): LedgerCategoriesComponent {
    const component = TestBed.runInInjectionContext(() => new LedgerCategoriesComponent());
    component.tree.set(tree);
    return component;
  }

  it('hides descendants when a category is collapsed', () => {
    const component = createComponent();

    component.toggleCategory({ stopPropagation: vi.fn() } as unknown as Event, food.uuid);

    expect(component.visibleRows().map(row => row.category.name)).toEqual(['Alimentação', 'Transporte']);
  });

  it('searches descendants by name and keeps their ancestor visible', () => {
    const component = createComponent();
    component.collapsed.set(new Set([food.uuid]));
    component.search.set('rest');

    expect(component.visibleRows().map(row => row.category.name)).toEqual(['Alimentação', 'Restaurantes']);
  });

  it('omits the visual trunk between the virtual root and top-level categories', () => {
    const component = createComponent();
    const rows = component.visibleRows();

    expect(rows[0].isRootBranch).toBe(true);
    expect(rows[0].isLast).toBe(false);
    expect(rows[1].isRootBranch).toBe(false);
    expect(rows[1].ancestorGuides).toEqual([]);
  });

  it('prevents dropping a category into one of its own descendants', () => {
    const component = createComponent();
    component.draggingUuid.set(food.uuid);

    expect(component.canDropOn(restaurants.uuid)).toBe(false);
    expect(component.canDropOn(transport.uuid)).toBe(true);
  });

  it('reparents a category through the existing update contract', () => {
    const component = createComponent();
    component.draggingUuid.set(food.uuid);
    const event = { preventDefault: vi.fn(), stopPropagation: vi.fn() } as unknown as DragEvent;

    component.drop(event, transport.uuid);

    expect(categoriesService.update).toHaveBeenCalledWith('ledger', food.uuid, {
      name: food.name,
      icon: food.icon,
      color_code: food.color_code,
      parent_uuid: transport.uuid,
    });
  });
});
