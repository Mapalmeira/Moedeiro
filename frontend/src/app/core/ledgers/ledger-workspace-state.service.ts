import { Injectable } from '@angular/core';
import { FinancialEventType } from './financial-events.models';
import { LedgerBudgetState } from './ledger-budgets.models';

type PeriodMode = 'month' | 'range';
type FlowMode = 'instant' | 'cumulative';
type EntitySection = 'account' | 'currency';

export interface ActivityFilterState {
  from_date: string;
  to_date: string;
  account_uuid: string;
  category_uuid: string;
  event_type: '' | FinancialEventType;
}

export interface HomeViewState {
  currency_uuid: string;
  flow_account_uuid: string;
  month: string;
  period_mode: PeriodMode;
  range_from_date: string;
  range_to_date: string;
  flow_mode: FlowMode;
}

export interface BudgetViewState {
  states: readonly LedgerBudgetState[];
  category_uuid: string;
  search: string;
}

export interface FlowViewState {
  account_uuid: string;
  month: string;
  period_mode: PeriodMode;
  range_from_date: string;
  range_to_date: string;
  detail_level: number;
}

export interface CategoryViewState {
  search: string;
  collapsed: readonly string[];
  root_collapsed: boolean;
}

interface LedgerWorkspaceState {
  activity?: ActivityFilterState;
  home?: HomeViewState;
  budgets?: BudgetViewState;
  flows?: FlowViewState;
  categories?: CategoryViewState;
  entitySearch?: Partial<Record<EntitySection, string>>;
}

@Injectable()
export class LedgerWorkspaceStateService {
  private readonly statesByLedgerUuid = new Map<string, LedgerWorkspaceState>();

  getActivity(ledgerUuid: string): ActivityFilterState | null {
    const state = this.statesByLedgerUuid.get(ledgerUuid)?.activity;
    return state ? { ...state } : null;
  }

  setActivity(ledgerUuid: string, state: ActivityFilterState): void {
    this.update(ledgerUuid, current => ({ ...current, activity: { ...state } }));
  }

  getHome(ledgerUuid: string): HomeViewState | null {
    const state = this.statesByLedgerUuid.get(ledgerUuid)?.home;
    return state ? { ...state } : null;
  }

  setHome(ledgerUuid: string, state: HomeViewState): void {
    this.update(ledgerUuid, current => ({ ...current, home: { ...state } }));
  }

  getBudgets(ledgerUuid: string): BudgetViewState | null {
    const state = this.statesByLedgerUuid.get(ledgerUuid)?.budgets;
    return state ? { ...state, states: [...state.states] } : null;
  }

  setBudgets(ledgerUuid: string, state: BudgetViewState): void {
    this.update(ledgerUuid, current => ({ ...current, budgets: { ...state, states: [...state.states] } }));
  }

  getFlows(ledgerUuid: string): FlowViewState | null {
    const state = this.statesByLedgerUuid.get(ledgerUuid)?.flows;
    return state ? { ...state } : null;
  }

  setFlows(ledgerUuid: string, state: FlowViewState): void {
    this.update(ledgerUuid, current => ({ ...current, flows: { ...state } }));
  }

  getCategoryView(ledgerUuid: string): CategoryViewState | null {
    const state = this.statesByLedgerUuid.get(ledgerUuid)?.categories;
    return state ? { ...state, collapsed: [...state.collapsed] } : null;
  }

  setCategoryView(ledgerUuid: string, state: CategoryViewState): void {
    this.update(ledgerUuid, current => ({ ...current, categories: { ...state, collapsed: [...state.collapsed] } }));
  }

  getEntitySearch(ledgerUuid: string, section: EntitySection): string | null {
    return this.statesByLedgerUuid.get(ledgerUuid)?.entitySearch?.[section] ?? null;
  }

  setEntitySearch(ledgerUuid: string, section: EntitySection, search: string): void {
    this.update(ledgerUuid, current => ({
      ...current,
      entitySearch: { ...current.entitySearch, [section]: search },
    }));
  }

  private update(ledgerUuid: string, change: (current: LedgerWorkspaceState) => LedgerWorkspaceState): void {
    this.statesByLedgerUuid.set(ledgerUuid, change(this.statesByLedgerUuid.get(ledgerUuid) ?? {}));
  }
}
