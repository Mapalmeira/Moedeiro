import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { catchError, Observable, tap, throwError } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import { PreferenceDefaultsService } from './preference-defaults.service';
import { UserPreferences } from './preferences.models';

@Injectable({ providedIn: 'root' })
export class PreferencesService {
  private readonly http = inject(HttpClient);
  private readonly defaults = inject(PreferenceDefaultsService);
  private readonly localState = signal<UserPreferences>(this.defaults.infer());

  /**
   * Last complete preferences state known by the frontend. It starts with a
   * plausible browser-derived value and is replaced whenever the backend is
   * read or successfully updated.
   */
  readonly current = this.localState.asReadonly();

  get(): Observable<UserPreferences> {
    return this.http.get<UserPreferences>(API_ROUTES.userPreferences, { withCredentials: true }).pipe(
      tap((preferences) => this.localState.set(preferences)),
    );
  }

  /**
   * Reads the persisted preferences. A 404 is a valid first-use state in the
   * current backend contract, so initialize them once from the browser.
   */
  getOrInitialize(): Observable<UserPreferences> {
    return this.get().pipe(
      catchError((error: unknown) => {
        if (error instanceof HttpErrorResponse && error.status === 404) {
          return this.save(this.defaults.infer());
        }
        return throwError(() => error);
      }),
    );
  }

  save(payload: UserPreferences): Observable<UserPreferences> {
    return this.http.put<UserPreferences>(API_ROUTES.userPreferences, payload, { withCredentials: true }).pipe(
      tap((preferences) => this.localState.set(preferences)),
    );
  }
}
