import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import {
  ChangePasswordRequest,
  ConfirmTotpRequest,
  DisableTotpRequest,
  StartTotpSetupRequest,
  TotpStatus,
  TotpResponse,
} from './security.models';

@Injectable({ providedIn: 'root' })
export class SecurityService {
  private readonly http = inject(HttpClient);

  readonly totpStatus = signal<TotpStatus>('unknown');

  changePassword(payload: ChangePasswordRequest): Observable<void> {
    return this.http.post<void>(API_ROUTES.password.change, payload);
  }

  getTotpStatus(): Observable<TotpResponse> {
    this.totpStatus.set('unknown');
    return this.http.get<TotpResponse>(API_ROUTES.totp.root).pipe(
      tap(({ state }) => this.totpStatus.set(state)),
    );
  }

  startTotpSetup(payload: StartTotpSetupRequest): Observable<TotpResponse> {
    return this.http.post<TotpResponse>(API_ROUTES.totp.setup, payload);
  }

  confirmTotp(payload: ConfirmTotpRequest): Observable<void> {
    return this.http.post<void>(API_ROUTES.totp.confirm, payload).pipe(
      tap(() => this.markTotpEnabled()),
    );
  }

  disableTotp(payload: DisableTotpRequest): Observable<void> {
    return this.http.delete<void>(API_ROUTES.totp.root, { body: payload }).pipe(
      tap(() => this.markTotpDisabled()),
    );
  }

  markTotpEnabled(): void {
    this.totpStatus.set('ENABLED');
  }

  markTotpDisabled(): void {
    this.totpStatus.set('DISABLED');
  }

  resetSessionState(): void {
    this.totpStatus.set('unknown');
  }
}
