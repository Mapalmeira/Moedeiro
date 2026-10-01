import { ComponentFixture, TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { CategoryParentSelectComponent, ROOT_CATEGORY_VALUE } from './category-parent-select.component';

const categories: LedgerCategory[] = [
  { uuid: 'home', name: 'Casa', parent_uuid: null, icon: 'lucide:House', color_code: '#21E683' },
  { uuid: 'market', name: 'Mercado', parent_uuid: 'home', icon: 'lucide:ShoppingCart', color_code: '#FFD51A' },
];

describe('CategoryParentSelectComponent', () => {
  let fixture: ComponentFixture<CategoryParentSelectComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [CategoryParentSelectComponent] });
    fixture = TestBed.createComponent(CategoryParentSelectComponent);
    fixture.componentRef.setInput('categories', categories);
    fixture.componentRef.setInput('value', ROOT_CATEGORY_VALUE);
    fixture.componentRef.setInput('rootLabel', 'Raiz');
    fixture.detectChanges();
  });

  it('filters case and accents while honoring excluded descendants', () => {
    fixture.componentRef.setInput('excludedUuids', new Set(['market']));
    fixture.detectChanges();
    fixture.componentInstance.updateQuery({ target: { value: 'casa' } } as unknown as Event);
    expect(fixture.componentInstance.filteredCategories()).toEqual([categories[0]]);

    fixture.componentInstance.updateQuery({ target: { value: 'mercado' } } as unknown as Event);
    expect(fixture.componentInstance.filteredCategories()).toEqual([]);
  });

  it('opens with the selected option active and emits a choice before closing', () => {
    fixture.componentRef.setInput('value', 'market');
    fixture.detectChanges();
    fixture.componentInstance.openList();
    expect(fixture.componentInstance.activeIndex()).toBe(2);

    const changed = vi.fn();
    fixture.componentInstance.valueChange.subscribe(changed);
    fixture.componentInstance.choose('home');
    expect(changed).toHaveBeenCalledWith('home');
    expect(fixture.componentInstance.open()).toBe(false);
  });

  it('supports keyboard selection of the root option', () => {
    const changed = vi.fn();
    fixture.componentInstance.valueChange.subscribe(changed);
    fixture.componentInstance.openList();
    fixture.componentInstance.handleSearchKeydown({ key: 'Enter', preventDefault: vi.fn() } as unknown as KeyboardEvent);

    expect(changed).toHaveBeenCalledWith(ROOT_CATEGORY_VALUE);
  });
});
