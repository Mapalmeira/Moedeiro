import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerBudgetOverview } from '../../../../core/ledgers/ledger-budgets.models';
import { LedgerBudgetsService } from '../../../../core/ledgers/ledger-budgets.service';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { LedgerAccount, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../../core/ledgers/ledger-entities.service';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { LedgerWorkspaceStateService } from '../../../../core/ledgers/ledger-workspace-state.service';
import { PreferencesService } from '../../../../core/preferences/preferences.service';
import { LedgerBudgetsComponent } from './ledger-budgets.component';

const account: LedgerAccount = {
  uuid: 'account',
  name: 'Conta',
  note: 'Principal',
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
  icon: 'lucide:Coins',
  color_code: '#FFD51A',
};

const category: LedgerCategory = {
  uuid: 'category',
  name: 'Casa',
  icon: 'lucide:House',
  color_code: '#488DFC',
  parent_uuid: null,
};

const budget: LedgerBudgetOverview = {
  uuid: 'budget',
  account_uuid: account.uuid,
  category_uuid: category.uuid,
  from_timestamp: 1_700_000_000,
  to_timestamp: 1_700_086_400,
  name: 'Mensal',
  description: null,
  amount: 100_00,
  state: 'ACTIVE',
  spent_amount: 25_00,
  fulfilled: null,
};

describe('LedgerBudgetsComponent', () => {
  const ledgerUuid = signal('');
  const language = signal<'pt-BR' | 'en'>('pt-BR');
  const preferences = signal({
    language: 'pt-BR' as const,
    theme: 'LIGHT' as const,
    timezone: 'UTC',
  });
  const budgetsService = {
    overview: vi.fn(() => of({ items: [budget], next_cursor: null })),
    delete: vi.fn(() => of(void 0)),
  };
  const entitiesService = {
    listAccounts: vi.fn(() => of([account])),
    listCurrencies: vi.fn(() => of([currency])),
  };
  const categoriesService = {
    getTree: vi.fn(() => of([{ category, children: [] }])),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    ledgerUuid.set('');
    budgetsService.overview.mockReturnValue(of({ items: [budget], next_cursor: null }));
    TestBed.configureTestingModule({
      providers: [
        LedgerWorkspaceStateService,
        { provide: LedgerBudgetsService, useValue: budgetsService },
        { provide: LedgerEntitiesService, useValue: entitiesService },
        { provide: LedgerCategoriesService, useValue: categoriesService },
        { provide: LedgerContextService, useValue: { ledgerUuid: ledgerUuid.asReadonly() } },
        { provide: PreferencesService, useValue: { current: preferences.asReadonly() } },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'error') } },
        { provide: I18nService, useValue: { language: language.asReadonly(), t: vi.fn((key: string) => key) } },
      ],
    });
  });

  it('loads the overview immediately after workspace resources finish loading', () => {
    const component = TestBed.runInInjectionContext(() => new LedgerBudgetsComponent());
    ledgerUuid.set('ledger');

    component.loadWorkspace();

    expect(budgetsService.overview).toHaveBeenCalledWith('ledger', expect.objectContaining({ states: ['ACTIVE', 'FUTURE', 'FINISHED'] }));
    expect(component.items()).toEqual([budget]);
    expect(component.cards()[0]?.stateIcon).toBe('clock');
    expect(component.resourcesLoading()).toBe(false);
  });
});
