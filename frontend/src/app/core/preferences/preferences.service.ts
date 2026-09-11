import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { catchError, Observable, tap, throwError } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import { I18nService } from '../i18n/i18n.service';
import { ThemeService } from '../theme/theme.service';
import { UserPreferences } from './preferences.models';

@Injectable({ providedIn: 'root' })
export class PreferencesService {
  private readonly http = inject(HttpClient);
  private readonly i18n = inject(I18nService);
  private readonly theme = inject(ThemeService);
  private readonly localState = signal<UserPreferences>(this.initialPreferences());

  /**
   * Last complete preferences state known by the frontend. It starts with a
   * plausible local value and is replaced whenever the backend is
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
   * current backend contract, so initialize them once from the current app state.
   */
  getOrInitialize(): Observable<UserPreferences> {
    return this.get().pipe(
      catchError((error: unknown) => {
        if (error instanceof HttpErrorResponse && error.status === 404) {
          return this.save(this.initialPreferences());
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

  private initialPreferences(): UserPreferences {
    return {
      language: this.i18n.language(),
      theme: this.theme.theme() === 'dark' ? 'DARK' : 'LIGHT',
    };
  }
}
