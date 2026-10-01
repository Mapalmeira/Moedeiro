import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { CategoryEditorComponent } from './category-editor.component';
import { ROOT_CATEGORY_VALUE } from './category-parent-select.component';

const root: LedgerCategory = { uuid: 'root', name: 'Home', parent_uuid: null, icon: 'lucide:House', color_code: '#21E683' };
const child: LedgerCategory = { uuid: 'child', name: 'Food', parent_uuid: 'root', icon: 'lucide:Utensils', color_code: '#FFD51A' };
const grandchild: LedgerCategory = { uuid: 'grandchild', name: 'Market', parent_uuid: 'child', icon: 'lucide:ShoppingCart', color_code: '#488DFC' };

describe('CategoryEditorComponent', () => {
  const categories = { create: vi.fn(() => of(root)), update: vi.fn(() => of(root)) };

  beforeEach(() => {
    vi.clearAllMocks();
    categories.create.mockReturnValue(of(root));
    categories.update.mockReturnValue(of(root));
    TestBed.configureTestingModule({
      imports: [CategoryEditorComponent],
      providers: [
        { provide: LedgerCategoriesService, useValue: categories },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'save failed') } },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
  });

  function createEditor(category: LedgerCategory | null = null): ComponentFixture<CategoryEditorComponent> {
    const fixture = TestBed.createComponent(CategoryEditorComponent);
    fixture.componentRef.setInput('ledgerUuid', 'ledger');
    fixture.componentRef.setInput('categories', [root, child, grandchild]);
    fixture.componentRef.setInput('category', category);
    fixture.detectChanges();
    return fixture;
  }

  it('creates a root category with normalized appearance', () => {
    const fixture = createEditor();
    fixture.componentInstance.form.setValue({ name: '  Home  ', parent: ROOT_CATEGORY_VALUE, icon: 'lucide:House', color_code: '#21e683' });

    fixture.componentInstance.save();

    expect(categories.create).toHaveBeenCalledWith('ledger', {
      name: 'Home', parent_uuid: null, icon: 'lucide:House', color_code: '#21E683',
    });
  });

  it('excludes the edited category and every descendant from parent choices', () => {
    const fixture = createEditor(root);
    expect(fixture.componentInstance.excludedParentUuids()).toEqual(new Set(['root', 'child', 'grandchild']));
  });

  it('updates an existing category through its identifier', () => {
    const fixture = createEditor(child);
    fixture.componentInstance.form.patchValue({ name: 'Updated', parent: ROOT_CATEGORY_VALUE });
    fixture.componentInstance.save();

    expect(categories.update).toHaveBeenCalledWith('ledger', 'child', expect.objectContaining({ name: 'Updated', parent_uuid: null }));
  });

  it('publishes backend failures and unlocks the editor', () => {
    categories.create.mockReturnValue(throwError(() => new Error('offline')));
    const fixture = createEditor();
    fixture.componentInstance.form.patchValue({ name: 'Home' });
    fixture.componentInstance.save();

    expect(fixture.componentInstance.error()).toBe('save failed');
    expect(fixture.componentInstance.saving()).toBe(false);
  });
});
