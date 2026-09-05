import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import { Ledger, LedgerPayload } from './ledger.models';

@Injectable({ providedIn: 'root' })
export class LedgerService {
  private readonly http = inject(HttpClient);
  private readonly ledgerState = signal<Ledger[]>([]);

  readonly ledgers = this.ledgerState.asReadonly();

  list(): Observable<Ledger[]> {
    return this.http.get<Ledger[]>(API_ROUTES.ledgers.root, { withCredentials: true }).pipe(
      tap((ledgers) => this.ledgerState.set(ledgers)),
    );
  }

  create(payload: LedgerPayload): Observable<Ledger> {
    return this.http.post<Ledger>(API_ROUTES.ledgers.root, payload, { withCredentials: true }).pipe(
      tap((ledger) => this.ledgerState.update((current) => [ledger, ...current])),
    );
  }

  access(ledgerUuid: string): Observable<Ledger> {
    return this.http.get<Ledger>(API_ROUTES.ledgers.one(ledgerUuid), { withCredentials: true }).pipe(
      tap((ledger) => this.replace(ledger)),
    );
  }

  update(ledgerUuid: string, payload: LedgerPayload): Observable<Ledger> {
    return this.http.put<Ledger>(API_ROUTES.ledgers.one(ledgerUuid), payload, { withCredentials: true }).pipe(
      tap((ledger) => this.replace(ledger)),
    );
  }

  delete(ledgerUuid: string): Observable<void> {
    return this.http.delete<void>(API_ROUTES.ledgers.one(ledgerUuid), { withCredentials: true }).pipe(
      tap(() => this.ledgerState.update((current) => current.filter((ledger) => ledger.uuid !== ledgerUuid))),
    );
  }

  private replace(next: Ledger): void {
    this.ledgerState.update((current) => current.map((ledger) => ledger.uuid === next.uuid ? next : ledger));
  }
}
