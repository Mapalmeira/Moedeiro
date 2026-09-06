import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import { LedgerAccount, LedgerAccountPayload, LedgerCurrency, LedgerCurrencyPayload } from './ledger-entities.models';

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
