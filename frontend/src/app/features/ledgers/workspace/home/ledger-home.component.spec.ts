import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { CashFlowService } from '../../../../core/ledgers/cash-flow.service';
import { FinancialEventsService } from '../../../../core/ledgers/financial-events.service';
import { LedgerBudgetsService } from '../../../../core/ledgers/ledger-budgets.service';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { LedgerWorkspaceStateService } from '../../../../core/ledgers/ledger-workspace-state.service';
import { LedgerAccount, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../../core/ledgers/ledger-entities.service';
import { PreferencesService } from '../../../../core/preferences/preferences.service';
import { LedgerHomeComponent } from './ledger-home.component';

const currency: LedgerCurrency = {
  uuid: 'currency',
  name: 'Real',
  prefix: 'R$ ',
  suffix: null,
  decimal_places: 2,
  icon: 'unicode:R$',
  color_code: '#21E683',
};

const point = {
  currency_uuid: currency.uuid,
  income: 100_00,
  expense: 40_00,
  event_count: 2,
  income_movement_count: 1,
  expense_movement_count: 1,
};

const account: LedgerAccount = {
  uuid: 'account',
  name: 'Principal',
  note: null,
  currency_uuid: currency.uuid,
  icon: 'lucide:WalletCards',
  color_code: '#21E683',
};

describe('LedgerHomeComponent', () => {
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
    listBalances: vi.fn(() => of({ items: [], total_balance: 0 })),
  };
  const categories = { getTree: vi.fn(() => of([])) };
  const events = { list: vi.fn(() => of({ events: [], next_cursor: null, total_count: 0 })) };
  const budgets = { currencyOverview: vi.fn(() => of([])) };
  const cashFlow = { summary: vi.fn(() => of(point)), points: vi.fn(() => of([point])) };

  beforeEach(() => {
    vi.clearAllMocks();
    ledgerUuid.set('ledger');
    TestBed.configureTestingModule({
      providers: [
        LedgerWorkspaceStateService,
        { provide: LedgerContextService, useValue: { ledgerUuid: ledgerUuid.asReadonly() } },
        { provide: LedgerEntitiesService, useValue: entities },
        { provide: LedgerCategoriesService, useValue: categories },
        { provide: FinancialEventsService, useValue: events },
        { provide: LedgerBudgetsService, useValue: budgets },
        { provide: CashFlowService, useValue: cashFlow },
        { provide: PreferencesService, useValue: { current: preferences.asReadonly() } },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'error') } },
        { provide: I18nService, useValue: { language: language.asReadonly(), t: vi.fn((key: string) => key) } },
      ],
    });
  });

  function createComponent(): LedgerHomeComponent {
    return TestBed.runInInjectionContext(() => new LedgerHomeComponent());
  }

  it('loads the dashboard after selecting the first available currency', () => {
    const component = createComponent();

    TestBed.tick();

    expect(entities.listCurrencies).toHaveBeenCalledWith('ledger');
    expect(component.selectedCurrencyUuid()).toBe(currency.uuid);
    expect(cashFlow.points).toHaveBeenCalledOnce();
    expect(component.cashFlow()).toEqual([point]);
    expect(component.totalIncome()).toBe(100_00);
    expect(component.totalExpense()).toBe(40_00);
  });

  it('filters only the period chart by the selected account', () => {
    const component = createComponent();
    TestBed.tick();

    component.selectFlowAccount(account.uuid);
    TestBed.tick();

    expect(cashFlow.points).toHaveBeenLastCalledWith(
      'ledger',
      currency.uuid,
      expect.any(Number),
      expect.any(Number),
      86_400,
      { account_uuid: account.uuid },
    );
    expect(TestBed.inject(LedgerWorkspaceStateService).getHome('ledger')?.flow_account_uuid).toBe(account.uuid);
    expect(component.totalIncome()).toBe(point.income);
    expect(component.totalExpense()).toBe(point.expense);
  });

  it('clears dashboard data and reports an invalid custom period', () => {
    const component = createComponent();
    TestBed.tick();
    expect(component.cashFlow()).toEqual([point]);

    component.setPeriodMode('range');
    component.updateRangeFrom('2026-09-10');
    component.updateRangeTo('2026-09-09');
    TestBed.tick();

    expect(component.invalidRange()).toBe(true);
    expect(component.dashboardRange()).toBeNull();
    expect(component.cashFlow()).toEqual([]);
    expect(component.balances()).toEqual([]);
    expect(cashFlow.points).toHaveBeenCalledOnce();
  });

  it('uses the selected period end for balances, budgets, and recent activity', () => {
    const component = createComponent();
    TestBed.tick();

    component.selectMonth('2026-07');
    TestBed.tick();

    const from = Date.parse('2026-07-01T00:00:00Z') / 1000;
    const to = Date.parse('2026-08-01T00:00:00Z') / 1000;
    const periodEnd = to - 1;
    expect(entities.listBalances).toHaveBeenLastCalledWith('ledger', periodEnd, currency.uuid, 5);
    expect(cashFlow.points).toHaveBeenLastCalledWith('ledger', currency.uuid, from, to, 86_400, { account_uuid: null });
    expect(events.list).toHaveBeenLastCalledWith('ledger', expect.objectContaining({
      from_timestamp: from,
      to_timestamp: to,
      currency_uuid: currency.uuid,
      ascending: false,
    }));
    expect(budgets.currencyOverview).toHaveBeenLastCalledWith('ledger', currency.uuid, periodEnd, 3);
  });

  it('pins the chart only for touch input and restores hover after a mouse movement', () => {
    const component = createComponent();
    TestBed.tick();
    const chart = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    vi.spyOn(chart, 'getBoundingClientRect').mockReturnValue({ left: 0, width: 1_000 } as DOMRect);
    const pointerEvent = (pointerType: string) => ({ pointerType, currentTarget: chart, clientX: 500 } as unknown as PointerEvent);

    component.pinChart(pointerEvent('touch'));
    expect(component.pinnedChartIndex()).toBe(0);

    component.hoverChart(pointerEvent('mouse'));
    expect(component.pinnedChartIndex()).toBeNull();
    expect(component.hoveredChartIndex()).toBe(0);

    component.pinChart(pointerEvent('mouse'));
    expect(component.pinnedChartIndex()).toBeNull();
  });

  it('clears a pinned chart point after an outside interaction', () => {
    const component = createComponent();
    component.pinnedChartIndex.set(0);

    component.clearChartSelectionOnOutsidePointerDown();

    expect(component.pinnedChartIndex()).toBeNull();
  });
});
