import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { LedgerAccount, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { FinancialEvent } from '../../../../core/ledgers/financial-events.models';
import { FinancialEventsService } from '../../../../core/ledgers/financial-events.service';
import { FinancialEventEditorComponent } from './financial-event-editor.component';

const currency: LedgerCurrency = { uuid: 'brl', name: 'Real', prefix: 'R$ ', suffix: null, decimal_places: 2, icon: 'lucide:Coins', color_code: '#21E683' };
const accounts: LedgerAccount[] = [
  { uuid: 'source', name: 'Source', note: null, currency_uuid: currency.uuid, icon: 'lucide:Wallet', color_code: '#21E683' },
  { uuid: 'destination', name: 'Destination', note: null, currency_uuid: currency.uuid, icon: 'lucide:Wallet', color_code: '#488DFC' },
];
const categories: LedgerCategory[] = [
  { uuid: 'root', name: 'Casa', icon: 'lucide:House', color_code: '#21E683', parent_uuid: null },
  { uuid: 'child', name: 'Mercado', icon: 'lucide:ShoppingBasket', color_code: '#FFD51A', parent_uuid: 'root' },
];
const savedEvent: FinancialEvent = { uuid: 'event', occurred_at: 1_700_000_000, description: 'Saved', type: 'TRANSACTION', movements: [] };

describe('FinancialEventEditorComponent', () => {
  const events = { create: vi.fn(() => of(savedEvent)), update: vi.fn(() => of(savedEvent)) };
  let fixture: ComponentFixture<FinancialEventEditorComponent>;

  beforeEach(async () => {
    vi.clearAllMocks();
    await TestBed.configureTestingModule({
      imports: [FinancialEventEditorComponent],
      providers: [
        { provide: FinancialEventsService, useValue: events },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'error') } },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(FinancialEventEditorComponent);
    fixture.componentRef.setInput('ledgerUuid', 'ledger');
    fixture.componentRef.setInput('type', 'TRANSACTION');
    fixture.componentRef.setInput('accounts', accounts);
    fixture.componentRef.setInput('currencies', [currency]);
    fixture.componentRef.setInput('categories', categories);
    fixture.detectChanges();
  });

  it('uses the shared category path helper for nested option details', () => {
    expect(fixture.componentInstance.categoryOptions()).toEqual([
      expect.objectContaining({ value: 'root', label: 'Casa', detail: null }),
      expect.objectContaining({ value: 'child', label: 'Mercado', detail: 'Casa › Mercado' }),
    ]);
  });

  it('builds a transaction create payload in minor units', () => {
    const component = fixture.componentInstance;
    component.form.patchValue({
      description: 'Mercado', date: '2026-09-11', time: '12:30:00', account_uuid: 'source', category_uuid: 'child', amount: '12.34', direction: 'EXPENSE',
    });

    component.save();

    expect(events.create).toHaveBeenCalledWith('ledger', expect.objectContaining({
      type: 'TRANSACTION', description: 'Mercado', account_uuid: 'source', category_uuid: 'child', value: -1234, quantity: 1, item_name: null, fee: null,
    }));
  });

  it('builds an optional fee for a simple expense', () => {
    const component = fixture.componentInstance;
    component.form.patchValue({
      description: 'Mercado', date: '2026-09-11', time: '12:30:00', account_uuid: 'source', category_uuid: 'child', amount: '12.34', direction: 'EXPENSE',
      fee_enabled: true, fee_amount: '1.25', fee_category_uuid: 'root',
    });

    component.save();

    expect(events.create).toHaveBeenCalledWith('ledger', expect.objectContaining({
      type: 'TRANSACTION', value: -1234, fee: { category_uuid: 'root', value: -125 },
    }));
  });

  it('loads a simple expense fee from the special movement marker', () => {
    const existing: FinancialEvent = {
      uuid: 'existing-with-fee', occurred_at: 1_700_000_000, description: 'Old', type: 'TRANSACTION',
      movements: [
        { uuid: 'main', account_uuid: 'source', category_uuid: 'child', value: -500, quantity: 1, item_name: null, special_type: null },
        { uuid: 'fee', account_uuid: 'source', category_uuid: 'root', value: -125, quantity: 1, item_name: null, special_type: 'FEE' },
      ],
    };
    fixture.componentRef.setInput('event', existing);
    fixture.detectChanges();

    expect(fixture.componentInstance.form.getRawValue()).toEqual(expect.objectContaining({
      account_uuid: 'source', category_uuid: 'child', amount: '5.00', direction: 'EXPENSE',
      fee_enabled: true, fee_amount: '1.25', fee_category_uuid: 'root',
    }));
  });

  it('uses the update contract when editing an existing transaction', () => {
    const existing: FinancialEvent = {
      uuid: 'existing', occurred_at: 1_700_000_000, description: 'Old', type: 'TRANSACTION',
      movements: [{ uuid: 'movement', account_uuid: 'source', category_uuid: 'child', value: -500, quantity: 1, item_name: null, special_type: null }],
    };
    fixture.componentRef.setInput('event', existing);
    fixture.detectChanges();
    const component = fixture.componentInstance;
    component.form.patchValue({ description: 'Updated', date: '2026-09-11', time: '12:30:00', amount: '7.50', direction: 'EXPENSE' });

    component.save();

    expect(events.update).toHaveBeenCalledWith('ledger', 'existing', expect.objectContaining({
      type: 'TRANSACTION', description: 'Updated', account_uuid: 'source', category_uuid: 'child', value: -750,
    }));
    expect(events.create).not.toHaveBeenCalled();
  });

  it('builds a same-currency transfer payload without a destination amount input', () => {
    fixture.componentRef.setInput('type', 'ACCOUNT_TRANSFER');
    fixture.detectChanges();
    const component = fixture.componentInstance;
    component.form.patchValue({
      description: 'Transfer', date: '2026-09-11', time: '12:30:00', source_account_uuid: 'source', destination_account_uuid: 'destination',
      category_uuid: 'child', source_amount: '25.00', destination_amount: '', fee_enabled: false,
    });

    component.save();

    expect(events.create).toHaveBeenCalledWith('ledger', expect.objectContaining({
      type: 'ACCOUNT_TRANSFER', source_account_uuid: 'source', source_value: -2500,
      destination_account_uuid: 'destination', destination_value: 2500, source_category_uuid: 'child', destination_category_uuid: 'child', fee: null,
    }));
  });
});
