import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { NavigationEnd, Router } from '@angular/router';
import { of, Subject } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nService } from '../../core/i18n/i18n.service';
import { PreferencesService } from '../../core/preferences/preferences.service';
import { ThemeService } from '../../core/theme/theme.service';
import { AuthenticatedLayoutComponent } from './authenticated-layout.component';
import { AuthenticatedShellService } from './authenticated-shell.service';

describe('AuthenticatedLayoutComponent', () => {
  const events = new Subject<NavigationEnd>();
  const router = { events, url: '/home' };
  const preferences = { getOrInitialize: vi.fn(() => of({ language: 'en' as const, theme: 'DARK' as const })) };
  const theme = { applyBackendPreference: vi.fn() };
  const i18n = { setLanguage: vi.fn(), t: vi.fn((key: string) => key) };
  const shell = {
    currentUserName: signal('alice'), loggingOut: signal(false), logoutError: signal<string | null>(null),
    preferencesOpen: signal(false), securityOpen: signal(false),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    router.url = '/home';
    TestBed.configureTestingModule({
      imports: [AuthenticatedLayoutComponent],
      providers: [
        { provide: Router, useValue: router },
        { provide: PreferencesService, useValue: preferences },
        { provide: ThemeService, useValue: theme },
        { provide: I18nService, useValue: i18n },
        { provide: AuthenticatedShellService, useValue: shell },
      ],
    });
    TestBed.overrideComponent(AuthenticatedLayoutComponent, { set: { template: '' } });
  });

  it('applies persisted language and theme during authenticated startup', () => {
    TestBed.createComponent(AuthenticatedLayoutComponent).detectChanges();

    expect(preferences.getOrInitialize).toHaveBeenCalledOnce();
    expect(theme.applyBackendPreference).toHaveBeenCalledWith('DARK');
    expect(i18n.setLanguage).toHaveBeenCalledWith('en');
  });

  it('tracks whether navigation is inside a ledger workspace', () => {
    const component = TestBed.createComponent(AuthenticatedLayoutComponent).componentInstance;
    expect(component.isLedgerRoute()).toBe(false);

    router.url = '/ledgers/ledger/home';
    events.next(new NavigationEnd(1, router.url, router.url));
    expect(component.isLedgerRoute()).toBe(true);
  });
});
