import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { catchError, map, Observable, of, switchMap, tap, throwError } from 'rxjs';
import { Router } from '@angular/router';
import { API_ROUTES } from '../api/api.routes';
import { LoginRequest, PasswordRecoveryRequest, RegistrationRequest } from './auth.models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  readonly authenticated = signal<boolean | null>(null);

  login(payload: LoginRequest): Observable<void> {
    return this.http.post<void>(API_ROUTES.authentication.login, payload, { withCredentials: true }).pipe(
      tap(() => this.authenticated.set(true)),
    );
  }

  register(payload: RegistrationRequest): Observable<void> {
    return this.http.post<void>(API_ROUTES.registration, payload, { withCredentials: true });
  }

  recoverPassword(payload: PasswordRecoveryRequest): Observable<void> {
    return this.http.post<void>(API_ROUTES.password.recovery, payload, { withCredentials: true });
  }

  validateSession(): Observable<boolean> {
    return this.http.get<void>(API_ROUTES.authentication.session, { withCredentials: true }).pipe(
      map(() => true),
      catchError(() => of(false)),
      tap((valid) => {
        this.authenticated.set(valid);
      }),
    );
  }

  ensureSession(): Observable<boolean> {
    return this.http.get<void>(API_ROUTES.authentication.session, { withCredentials: true }).pipe(
      map(() => true),
      catchError((error: HttpErrorResponse) => {
        if (error.status !== 401) {
          return of(false);
        }
        return this.http.post<void>(API_ROUTES.authentication.refresh, {}, { withCredentials: true }).pipe(
          switchMap(() => this.http.get<void>(API_ROUTES.authentication.session, { withCredentials: true })),
          map(() => true),
          catchError(() => of(false)),
        );
      }),
      tap((valid) => {
        this.authenticated.set(valid);
      }),
    );
  }

  logout(): Observable<void> {
    return this.http.post<void>(API_ROUTES.authentication.logout, {}, { withCredentials: true }).pipe(
      catchError((error) => {
        // Mesmo se o servidor já considerar a sessão inválida, o front deve sair da área protegida.
        if (error instanceof HttpErrorResponse && error.status === 401) {
          return of(void 0);
        }
        return throwError(() => error);
      }),
      tap(() => {
        this.authenticated.set(false);
      }),
    );
  }

  async finishLogout(state?: Record<string, unknown>): Promise<void> {
    this.authenticated.set(false);
    await this.router.navigateByUrl('/', state ? { state } : undefined);
  }
}
