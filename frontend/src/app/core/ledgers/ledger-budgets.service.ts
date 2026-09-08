import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import {
  CreateLedgerBudgetPayload,
  LedgerBudget,
  LedgerBudgetOverview,
  LedgerBudgetOverviewPage,
  LedgerBudgetState,
  UpdateLedgerBudgetPayload,
} from './ledger-budgets.models';

@Injectable({ providedIn: 'root' })
export class LedgerBudgetsService {
  private readonly http = inject(HttpClient);

  overview(
    ledgerUuid: string,
    options: { states: readonly LedgerBudgetState[]; pageSize: number; search?: string | null; accountUuid?: string | null; cursor?: string | null },
  ): Observable<LedgerBudgetOverviewPage> {
    let params = new HttpParams().set('page_size', options.pageSize);
    for (const state of options.states) params = params.append('state', state);
    if (options.search?.trim()) params = params.set('search', options.search.trim());
    if (options.accountUuid) params = params.set('account_uuid', options.accountUuid);
    if (options.cursor) params = params.set('cursor', options.cursor);
    return this.http.get<LedgerBudgetOverviewPage>(`${API_ROUTES.ledgerBudgets(ledgerUuid)}/overview`, { params, withCredentials: true });
  }

  attention(ledgerUuid: string, accountUuid: string, limit = 3): Observable<LedgerBudgetOverview[]> {
    return this.http.get<LedgerBudgetOverview[]>(`${API_ROUTES.ledgerBudgets(ledgerUuid)}/attention`, {
      params: { account_uuid: accountUuid, limit },
      withCredentials: true,
    });
  }

  get(ledgerUuid: string, budgetUuid: string): Observable<LedgerBudget> {
    return this.http.get<LedgerBudget>(`${API_ROUTES.ledgerBudgets(ledgerUuid)}/${encodeURIComponent(budgetUuid)}`, { withCredentials: true });
  }

  create(ledgerUuid: string, payload: CreateLedgerBudgetPayload): Observable<LedgerBudget> {
    return this.http.post<LedgerBudget>(API_ROUTES.ledgerBudgets(ledgerUuid), payload, { withCredentials: true });
  }

  update(ledgerUuid: string, budgetUuid: string, payload: UpdateLedgerBudgetPayload): Observable<LedgerBudget> {
    return this.http.put<LedgerBudget>(`${API_ROUTES.ledgerBudgets(ledgerUuid)}/${encodeURIComponent(budgetUuid)}`, payload, { withCredentials: true });
  }

  delete(ledgerUuid: string, budgetUuid: string): Observable<void> {
    return this.http.delete<void>(`${API_ROUTES.ledgerBudgets(ledgerUuid)}/${encodeURIComponent(budgetUuid)}`, { withCredentials: true });
  }
}
