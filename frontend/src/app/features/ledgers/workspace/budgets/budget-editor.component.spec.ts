import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerBudget } from '../../../../core/ledgers/ledger-budgets.models';
import { LedgerBudgetsService } from '../../../../core/ledgers/ledger-budgets.service';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { LedgerAccount, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { BudgetEditorComponent } from './budget-editor.component';

const currency: LedgerCurrency = { uuid: 'currency', name: 'Real', prefix: 'R$ ', suffix: null, decimal_places: 2, icon: 'lucide:Coins', color_code: '#FFD51A' };
const otherCurrency: LedgerCurrency = { ...currency, uuid: 'other-currency', name: 'Dollar' };
const account: LedgerAccount = { uuid: 'account', name: 'Checking', note: null, currency_uuid: currency.uuid, icon: 'lucide:Wallet', color_code: '#21E683' };
const otherAccount: LedgerAccount = { ...account, uuid: 'other-account', currency_uuid: otherCurrency.uuid };
const category: LedgerCategory = { uuid: 'category', name: 'Food', parent_uuid: null, icon: 'lucide:Utensils', color_code: '#488DFC' };
const budget: LedgerBudget = { uuid: 'budget', account_uuid: account.uuid, category_uuid: category.uuid, from_timestamp: 1_767_225_600, to_timestamp: 1_769_904_000, name: 'January', description: null, amount: 10000 };

describe('BudgetEditorComponent', () => {
  const budgets = { create: vi.fn(() => of(budget)), update: vi.fn(() => of(budget)) };
  let fixture: ComponentFixture<BudgetEditorComponent>;

  beforeEach(() => {
    vi.clearAllMocks();
    budgets.create.mockReturnValue(of(budget));
    budgets.update.mockReturnValue(of(budget));
    TestBed.configureTestingModule({
      imports: [BudgetEditorComponent],
      providers: [
        { provide: LedgerBudgetsService, useValue: budgets },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'save failed') } },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
    fixture = TestBed.createComponent(BudgetEditorComponent);
    fixture.componentRef.setInput('ledgerUuid', 'ledger');
    fixture.componentRef.setInput('accounts', [account, otherAccount]);
    fixture.componentRef.setInput('currencies', [currency, otherCurrency]);
    fixture.componentRef.setInput('categories', [category]);
    fixture.detectChanges();
  });

  function fillValidForm(): void {
    fixture.componentInstance.form.setValue({
      name: '  Monthly food  ', description: '  Groceries  ', account_uuid: 'account', category_uuid: 'category',
      from_date: '2026-01-01', to_date: '2026-01-31', amount: '100.25',
    });
  }

  it('creates a budget in minor units with an inclusive selected end date', () => {
    fillValidForm();
    fixture.componentInstance.save();

    expect(budgets.create).toHaveBeenCalledWith('ledger', {
      account_uuid: 'account', category_uuid: 'category',
      from_timestamp: Math.floor(new Date('2026-01-01T00:00:00').getTime() / 1000),
      to_timestamp: Math.floor(new Date('2026-02-01T00:00:00').getTime() / 1000),
      name: 'Monthly food', description: 'Groceries', amount: 10025,
    });
  });

  it('keeps an existing budget account immutable during update', () => {
    fixture.componentRef.setInput('budget', budget);
    fixture.detectChanges();
    fixture.componentInstance.setAccount('other-account');
    expect(fixture.componentInstance.form.controls.account_uuid.value).toBe('account');

    fixture.componentInstance.save();
    expect(budgets.update).toHaveBeenCalledWith('ledger', 'budget', expect.not.objectContaining({ account_uuid: expect.anything() }));
  });

  it('clears an entered amount when switching to another currency', () => {
    fixture.componentInstance.setAccount('account');
    fixture.componentInstance.setAmount('10.00');
    fixture.componentInstance.setAccount('other-account');

    expect(fixture.componentInstance.form.controls.amount.value).toBe('');
  });

  it('rejects impossible periods and invalid currency amounts locally', () => {
    fillValidForm();
    fixture.componentInstance.form.patchValue({ from_date: '2026-02-01', to_date: '2026-01-31' });
    fixture.componentInstance.save();
    expect(fixture.componentInstance.error()).toBe('budgets.validation.period');

    fillValidForm();
    fixture.componentInstance.form.controls.amount.setValue('invalid');
    fixture.componentInstance.save();
    expect(fixture.componentInstance.error()).toBe('budgets.validation.amount');
    expect(budgets.create).not.toHaveBeenCalled();
  });

  it('publishes backend failures and unlocks the editor', () => {
    budgets.create.mockReturnValue(throwError(() => new Error('offline')));
    fillValidForm();
    fixture.componentInstance.save();

    expect(fixture.componentInstance.error()).toBe('save failed');
    expect(fixture.componentInstance.saving()).toBe(false);
  });
});
