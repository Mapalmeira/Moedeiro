import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import { LedgerAccount, LedgerAccountBalanceList, LedgerAccountPayload, LedgerCurrency, LedgerCurrencyPayload } from './ledger-entities.models';

@Injectable({ providedIn: 'root' })
export class LedgerEntitiesService {
  private readonly http = inject(HttpClient);

  listAccounts(ledgerUuid: string): Observable<LedgerAccount[]> {
    return this.http.get<LedgerAccount[]>(API_ROUTES.ledgerAccounts(ledgerUuid), { withCredentials: true });
  }

  createAccount(ledgerUuid: string, payload: LedgerAccountPayload): Observable<LedgerAccount> {
    return this.http.post<LedgerAccount>(API_ROUTES.ledgerAccounts(ledgerUuid), payload, { withCredentials: true });
  }

  updateAccount(ledgerUuid: string, accountUuid: string, payload: Omit<LedgerAccountPayload, 'currency_uuid'>): Observable<LedgerAccount> {
    return this.http.put<LedgerAccount>(`${API_ROUTES.ledgerAccounts(ledgerUuid)}/${encodeURIComponent(accountUuid)}`, payload, { withCredentials: true });
  }

  deleteAccount(ledgerUuid: string, accountUuid: string): Observable<void> {
    return this.http.delete<void>(`${API_ROUTES.ledgerAccounts(ledgerUuid)}/${encodeURIComponent(accountUuid)}`, { withCredentials: true });
  }

  getAccountBalance(ledgerUuid: string, accountUuid: string, timestamp: number): Observable<number> {
    return this.http.get<number>(API_ROUTES.ledgerAccountBalance(ledgerUuid, accountUuid), {
      params: { timestamp },
      withCredentials: true,
    });
  }

  listBalances(ledgerUuid: string, timestamp: number, currencyUuid?: string | null, limit?: number | null): Observable<LedgerAccountBalanceList> {
    const params: Record<string, string | number> = { timestamp };
    if (currencyUuid) params['currency_uuid'] = currencyUuid;
    if (limit) params['limit'] = limit;
    return this.http.get<LedgerAccountBalanceList>(API_ROUTES.ledgerBalances(ledgerUuid), { params, withCredentials: true });
  }

  listCurrencies(ledgerUuid: string): Observable<LedgerCurrency[]> {
    return this.http.get<LedgerCurrency[]>(API_ROUTES.ledgerCurrencies(ledgerUuid), { withCredentials: true });
  }

  createCurrency(ledgerUuid: string, payload: LedgerCurrencyPayload): Observable<LedgerCurrency> {
    return this.http.post<LedgerCurrency>(API_ROUTES.ledgerCurrencies(ledgerUuid), payload, { withCredentials: true });
  }

  updateCurrency(ledgerUuid: string, currencyUuid: string, payload: Omit<LedgerCurrencyPayload, 'decimal_places'>): Observable<LedgerCurrency> {
    return this.http.put<LedgerCurrency>(`${API_ROUTES.ledgerCurrencies(ledgerUuid)}/${encodeURIComponent(currencyUuid)}`, payload, { withCredentials: true });
  }

  deleteCurrency(ledgerUuid: string, currencyUuid: string): Observable<void> {
    return this.http.delete<void>(`${API_ROUTES.ledgerCurrencies(ledgerUuid)}/${encodeURIComponent(currencyUuid)}`, { withCredentials: true });
  }
}
