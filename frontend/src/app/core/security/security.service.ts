import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import {
  ChangePasswordRequest,
  ConfirmTotpRequest,
  DisableTotpRequest,
  StartTotpSetupRequest,
  StartTotpSetupResponse,
  TotpStatus,
  TotpStatusResponse,
} from './security.models';

@Injectable({ providedIn: 'root' })
export class SecurityService {
  private readonly http = inject(HttpClient);

  readonly totpStatus = signal<TotpStatus>('unknown');

  changePassword(payload: ChangePasswordRequest): Observable<void> {
    return this.http.post<void>(API_ROUTES.password.change, payload, { withCredentials: true });
  }

  getTotpStatus(): Observable<TotpStatusResponse> {
    this.totpStatus.set('unknown');
    return this.http.get<TotpStatusResponse>(API_ROUTES.totp.root, { withCredentials: true }).pipe(
      tap(({ enabled }) => this.totpStatus.set(enabled ? 'enabled' : 'disabled')),
    );
  }

  startTotpSetup(payload: StartTotpSetupRequest): Observable<StartTotpSetupResponse> {
    return this.http.post<StartTotpSetupResponse>(API_ROUTES.totp.setup, payload, { withCredentials: true });
  }

  confirmTotp(payload: ConfirmTotpRequest): Observable<void> {
    return this.http.post<void>(API_ROUTES.totp.confirm, payload, { withCredentials: true }).pipe(
      tap(() => this.markTotpEnabled()),
    );
  }

  disableTotp(payload: DisableTotpRequest): Observable<void> {
    return this.http.delete<void>(API_ROUTES.totp.root, { body: payload, withCredentials: true }).pipe(
      tap(() => this.markTotpDisabled()),
    );
  }

  markTotpEnabled(): void {
    this.totpStatus.set('enabled');
  }

  markTotpDisabled(): void {
    this.totpStatus.set('disabled');
  }

  resetSessionState(): void {
    this.totpStatus.set('unknown');
  }
}
