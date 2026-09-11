import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { catchError, finalize, map, Observable, of, shareReplay, switchMap, tap, throwError } from 'rxjs';
import { Router } from '@angular/router';
import { API_ROUTES } from '../api/api.routes';
import { AuthenticationSession, LoginRequest, PasswordRecoveryRequest, RegistrationRequest } from './auth.models';

const AUTH_NAME_STORAGE_KEY = 'moedeiro.last-auth-name';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  readonly authenticated = signal<boolean | null>(null);
  readonly currentUserName = signal<string | null>(this.readStoredUserName());
  private refreshRequest: Observable<boolean> | null = null;

  login(payload: LoginRequest): Observable<void> {
    return this.http.post<void>(API_ROUTES.authentication.login, payload).pipe(
      tap(() => {
        this.authenticated.set(true);
        this.storeUserName(payload.name);
      }),
    );
  }

  register(payload: RegistrationRequest): Observable<void> {
    return this.http.post<void>(API_ROUTES.registration, payload);
  }

  recoverPassword(payload: PasswordRecoveryRequest): Observable<void> {
    return this.http.post<void>(API_ROUTES.password.recovery, payload);
  }

  validateSession(): Observable<boolean> {
    return this.http.get<AuthenticationSession>(API_ROUTES.authentication.session).pipe(
      tap((session) => this.storeUserName(session.name)),
      map(() => true),
      catchError(() => of(false)),
      tap((valid) => {
        this.authenticated.set(valid);
        if (!valid) this.storeUserName(null);
      }),
    );
  }

  ensureSession(): Observable<boolean> {
    if (this.authenticated() === true) return of(true);

    return this.http.get<AuthenticationSession>(API_ROUTES.authentication.session).pipe(
      tap((session) => this.storeUserName(session.name)),
      map(() => true),
      catchError((error: HttpErrorResponse) => error.status === 401 ? this.refreshSession() : of(false)),
      tap((valid) => this.commitSessionState(valid)),
    );
  }

  refreshSession(): Observable<boolean> {
    if (this.refreshRequest) return this.refreshRequest;

    const request = this.http.post<void>(API_ROUTES.authentication.refresh, {}).pipe(
      switchMap(() => this.http.get<AuthenticationSession>(API_ROUTES.authentication.session)),
      tap((session) => this.storeUserName(session.name)),
      map(() => true),
      catchError(() => of(false)),
      tap((valid) => this.commitSessionState(valid)),
      finalize(() => {
        this.refreshRequest = null;
      }),
      shareReplay({ bufferSize: 1, refCount: false }),
    );
    this.refreshRequest = request;
    return request;
  }

  logout(): Observable<void> {
    return this.http.post<void>(API_ROUTES.authentication.logout, {}).pipe(
      catchError((error) => {
        if (error instanceof HttpErrorResponse && error.status === 401) {
          return of(void 0);
        }
        return throwError(() => error);
      }),
      tap(() => {
        this.authenticated.set(false);
        this.storeUserName(null);
      }),
    );
  }

  async finishLogout(state?: Record<string, unknown>): Promise<void> {
    this.authenticated.set(false);
    this.storeUserName(null);
    await this.router.navigateByUrl('/', state ? { state } : undefined);
  }

  private commitSessionState(valid: boolean): void {
    this.authenticated.set(valid);
    if (!valid) this.storeUserName(null);
  }

  private storeUserName(name: string | null): void {
    this.currentUserName.set(name);

    if (typeof localStorage === 'undefined') return;
    if (!name) {
      localStorage.removeItem(AUTH_NAME_STORAGE_KEY);
      return;
    }
    localStorage.setItem(AUTH_NAME_STORAGE_KEY, name);
  }

  private readStoredUserName(): string | null {
    if (typeof localStorage === 'undefined') return null;
    return localStorage.getItem(AUTH_NAME_STORAGE_KEY);
  }
}
