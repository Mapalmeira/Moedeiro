import { HttpErrorResponse } from '@angular/common/http';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
import { I18nService } from '../i18n/i18n.service';
import { ThemeService } from '../theme/theme.service';
import { PreferencesService } from './preferences.service';

describe('PreferencesService', () => {
  const language = signal<'pt-BR' | 'en'>('pt-BR');
  const theme = signal<'light' | 'dark'>('dark');
  let service: PreferencesService;
  let http: HttpTestingController;

  beforeEach(() => {
    language.set('pt-BR');
    theme.set('dark');
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: I18nService, useValue: { language: language.asReadonly() } },
        { provide: ThemeService, useValue: { theme: theme.asReadonly() } },
      ],
    });
    service = TestBed.inject(PreferencesService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('starts with the current local language and theme', () => {
    expect(service.current()).toEqual({ language: 'pt-BR', theme: 'DARK' });
  });

  it('stores preferences returned by the backend', () => {
    service.get().subscribe();
    http.expectOne(API_ROUTES.userPreferences).flush({ language: 'en', theme: 'LIGHT' });

    expect(service.current()).toEqual({ language: 'en', theme: 'LIGHT' });
  });

  it('initializes missing backend preferences from the local state', () => {
    service.getOrInitialize().subscribe();
    http.expectOne(API_ROUTES.userPreferences).flush(null, { status: 404, statusText: 'Not Found' });
    const initialization = http.expectOne(API_ROUTES.userPreferences);

    expect(initialization.request.method).toBe('PUT');
    expect(initialization.request.body).toEqual({ language: 'pt-BR', theme: 'DARK' });
    initialization.flush({ language: 'pt-BR', theme: 'DARK' });
  });

  it('does not replace a backend failure with initialization', () => {
    let failure: unknown;
    service.getOrInitialize().subscribe({ error: (error) => failure = error });
    http.expectOne(API_ROUTES.userPreferences).flush(null, { status: 503, statusText: 'Unavailable' });

    expect(failure).toBeInstanceOf(HttpErrorResponse);
    http.expectNone(candidate => candidate.method === 'PUT');
  });

  it('saves and publishes the backend response', () => {
    service.save({ language: 'en', theme: 'LIGHT' }).subscribe();
    const request = http.expectOne(API_ROUTES.userPreferences);

    expect(request.request.method).toBe('PUT');
    expect(request.request.body).toEqual({ language: 'en', theme: 'LIGHT' });
    request.flush({ language: 'en', theme: 'LIGHT' });
    expect(service.current()).toEqual({ language: 'en', theme: 'LIGHT' });
  });
});
