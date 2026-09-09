import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Subject, of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { CashFlowSankey } from '../../../../core/ledgers/cash-flow.models';
import { CashFlowService } from '../../../../core/ledgers/cash-flow.service';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { LedgerAccount, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../../core/ledgers/ledger-entities.service';
import { PreferencesService } from '../../../../core/preferences/preferences.service';
import { LedgerFlowsComponent } from './ledger-flows.component';

const account: LedgerAccount = {
  uuid: 'account',
  name: 'Principal',
  note: null,
  currency_uuid: 'currency',
  icon: 'lucide:Wallet',
  color_code: '#21E683',
};

const currency: LedgerCurrency = {
  uuid: 'currency',
  name: 'Real',
  prefix: 'R$ ',
  suffix: null,
  decimal_places: 2,
  icon: 'unicode:R$',
  color_code: '#21E683',
};

const graph: CashFlowSankey = {
  account_uuid: account.uuid,
  currency_uuid: currency.uuid,
  from_timestamp: 0,
  to_timestamp: 1,
  detail_level: 3,
  income: 100_00,
  expense: 40_00,
  nodes: [],
  links: [],
};

describe('LedgerFlowsComponent', () => {
  const ledgerUuid = signal('ledger');
  const language = signal<'pt-BR' | 'en'>('pt-BR');
  const preferences = signal({
    language: 'pt-BR' as const,
    date_format: 'DMY' as const,
    time_format: 'H24' as const,
    number_format: 'COMMA' as const,
    theme: 'LIGHT' as const,
    timezone: 'UTC',
  });
  const entities = {
    listAccounts: vi.fn(() => of([account])),
    listCurrencies: vi.fn(() => of([currency])),
  };
  const cashFlow = { sankey: vi.fn(() => of(graph)) };
  const errors = { message: vi.fn(() => 'translated error') };

  beforeEach(() => {
    vi.clearAllMocks();
    ledgerUuid.set('ledger');
    entities.listAccounts.mockReturnValue(of([account]));
    entities.listCurrencies.mockReturnValue(of([currency]));
    cashFlow.sankey.mockReturnValue(of(graph));
    TestBed.configureTestingModule({
      providers: [
        { provide: LedgerContextService, useValue: { ledgerUuid: ledgerUuid.asReadonly() } },
        { provide: LedgerEntitiesService, useValue: entities },
        { provide: CashFlowService, useValue: cashFlow },
        { provide: PreferencesService, useValue: { current: preferences.asReadonly() } },
        { provide: ApiErrorService, useValue: errors },
        { provide: I18nService, useValue: { language: language.asReadonly(), t: vi.fn((key: string) => key) } },
      ],
    });
  });

  function createComponent(): LedgerFlowsComponent {
    return TestBed.runInInjectionContext(() => new LedgerFlowsComponent());
  }

  function prepareGraphRequest(component: LedgerFlowsComponent): void {
    component.accounts.set([account]);
    component.currencies.set([currency]);
    component.selectedAccountUuid.set(account.uuid);
    component.selectedMonth.set('2026-09');
    component.resourcesReady.set(true);
  }

  it('reacts to the ledger context by loading resources and the initial graph', () => {
    const component = createComponent();

    TestBed.tick();

    expect(entities.listAccounts).toHaveBeenCalledWith('ledger');
    expect(entities.listCurrencies).toHaveBeenCalledWith('ledger');
    expect(component.selectedAccountUuid()).toBe(account.uuid);
    expect(component.selectedCurrency()).toEqual(currency);
    expect(component.resourcesReady()).toBe(true);
    expect(component.resourcesLoading()).toBe(false);
    expect(cashFlow.sankey).toHaveBeenCalledOnce();
    expect(component.graph()).toEqual(graph);
  });

  it('uses a half-open month range in the preferred time zone', () => {
    const component = createComponent();
    prepareGraphRequest(component);

    component.retry();

    expect(cashFlow.sankey).toHaveBeenCalledWith(
      'ledger',
      account.uuid,
      Date.parse('2026-09-01T00:00:00Z') / 1000,
      Date.parse('2026-10-01T00:00:00Z') / 1000,
      3,
    );
    expect(component.graph()).toEqual(graph);
    expect(component.loading()).toBe(false);
  });

  it('clears a stale graph while its replacement is loading', () => {
    const response = new Subject<CashFlowSankey>();
    cashFlow.sankey.mockReturnValue(response);
    const component = createComponent();
    prepareGraphRequest(component);
    component.graph.set(graph);

    component.retry();

    expect(component.graph()).toBeNull();
    expect(component.loading()).toBe(true);

    response.next(graph);
    response.complete();
    expect(component.graph()).toEqual(graph);
    expect(component.loading()).toBe(false);
  });

  it('rejects reversed and impossible custom ranges without making a request', () => {
    const component = createComponent();
    prepareGraphRequest(component);
    component.periodMode.set('range');
    component.rangeFromDate.set('2026-09-10');
    component.rangeToDate.set('2026-09-09');

    expect(component.invalidRange()).toBe(true);
    component.retry();

    component.rangeFromDate.set('2026-02-01');
    component.rangeToDate.set('2026-02-31');
    expect(component.invalidRange()).toBe(true);
    component.retry();

    expect(cashFlow.sankey).not.toHaveBeenCalled();
  });

  it('exposes resource failures and succeeds when retried', () => {
    entities.listAccounts.mockReturnValue(throwError(() => new Error('offline')));
    const component = createComponent();

    component.retry();

    expect(errors.message).toHaveBeenCalledWith(expect.any(Error), 'errors.flowsLoadFailed');
    expect(component.error()).toBe('translated error');
    expect(component.resourcesLoading()).toBe(false);

    entities.listAccounts.mockReturnValue(of([account]));
    component.retry();
    expect(component.error()).toBeNull();
    expect(component.resourcesReady()).toBe(true);
  });
});
