import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Subject, of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { CashFlowService } from '../../../../core/ledgers/cash-flow.service';
import { formatCurrencyAmount } from '../../../../core/ledgers/currency-format';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { LedgerEntitiesService } from '../../../../core/ledgers/ledger-entities.service';
import { LedgerAccount, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { FinancialEvent, FinancialEventPage } from '../../../../core/ledgers/financial-events.models';
import { FinancialEventsService } from '../../../../core/ledgers/financial-events.service';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { LedgerWorkspaceStateService } from '../../../../core/ledgers/ledger-workspace-state.service';
import { LedgerActivityComponent } from './ledger-activity.component';

describe('LedgerActivityComponent', () => {
  const ledgerUuid = signal<string | null>(null);
  const events = { list: vi.fn(), delete: vi.fn(() => of(void 0)) };
  const currency: LedgerCurrency = { uuid: 'brl', name: 'Real', prefix: 'R$ ', suffix: null, decimal_places: 2, icon: 'lucide:Coins', color_code: '#21E683' };
  const source: LedgerAccount = { uuid: 'source', name: 'Source', note: null, currency_uuid: currency.uuid, icon: 'lucide:Wallet', color_code: '#21E683' };
  const destination: LedgerAccount = { uuid: 'destination', name: 'Destination', note: null, currency_uuid: currency.uuid, icon: 'lucide:Wallet', color_code: '#21E683' };

  beforeEach(() => {
    vi.clearAllMocks();
    ledgerUuid.set(null);
    TestBed.configureTestingModule({
      providers: [
        LedgerWorkspaceStateService,
        { provide: LedgerContextService, useValue: { ledgerUuid: ledgerUuid.asReadonly() } },
        { provide: FinancialEventsService, useValue: events },
        { provide: LedgerEntitiesService, useValue: { listAccounts: vi.fn(), listCurrencies: vi.fn(), getAccountBalance: vi.fn() } },
        { provide: LedgerCategoriesService, useValue: { getTree: vi.fn() } },
        { provide: CashFlowService, useValue: { summary: vi.fn() } },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'error') } },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
  });

  it('keeps loading active when an events request is replaced', () => {
    const first = new Subject<FinancialEventPage>();
    const second = new Subject<FinancialEventPage>();
    events.list.mockReturnValueOnce(first).mockReturnValueOnce(second);
    const component = TestBed.runInInjectionContext(() => new LedgerActivityComponent());
    ledgerUuid.set('ledger');
    component.setPeriodMode('range');
    component.setRangeDate('from_date', '2026-09-01');
    component.setRangeDate('to_date', '2026-09-30');

    component.applyFilters();
    expect(component.loading()).toBe(true);

    component.applyFilters();

    expect(component.loading()).toBe(true);
    second.next({ events: [], next_cursor: null, total_count: 0 });
    second.complete();
    expect(component.loading()).toBe(false);
  });

  it('aggregates only the selected account side of a transfer', () => {
    const component = TestBed.runInInjectionContext(() => new LedgerActivityComponent());
    const transfer: FinancialEvent = {
      uuid: 'transfer',
      occurred_at: 100,
      description: 'Transfer',
      type: 'ACCOUNT_TRANSFER',
      movements: [
        { uuid: 'outgoing', account_uuid: source.uuid, category_uuid: 'category', value: -10_000, quantity: 1, item_name: null },
        { uuid: 'incoming', account_uuid: destination.uuid, category_uuid: 'category', value: 10_000, quantity: 1, item_name: null },
      ],
    };
    const filters = { from_timestamp: 0, to_timestamp: 200, page_size: 40, account_uuid: source.uuid };
    component.accounts.set([source, destination]);
    component.currencies.set([currency]);
    component.events.set([transfer]);
    component.appliedFilters.set(filters);

    expect(component.eventRows()[0].value).toBe(formatCurrencyAmount(-10_000, currency));
    expect(component.eventRows()[0].valueTone).toBe('negative');

    component.appliedFilters.set({ ...filters, account_uuid: destination.uuid });

    expect(component.eventRows()[0].value).toBe(formatCurrencyAmount(10_000, currency));
    expect(component.eventRows()[0].valueTone).toBe('positive');
  });

});
