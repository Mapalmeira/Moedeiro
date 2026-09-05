import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';
import { AuthenticatedShellService } from './authenticated-shell.service';

describe('AuthenticatedShellService', () => {
  const auth = {
    currentUserName: { asReadonly: vi.fn(() => () => 'user') },
    logout: vi.fn(() => of(undefined)),
    finishLogout: vi.fn(() => Promise.resolve()),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    auth.logout.mockReturnValue(of(undefined));

    TestBed.configureTestingModule({
      providers: [
        AuthenticatedShellService,
        { provide: AuthService, useValue: auth },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'logout error') } },
      ],
    });
  });

  it('owns the authenticated dialogs for every nested layout', () => {
    const shell = TestBed.inject(AuthenticatedShellService);

    shell.openPreferences();
    expect(shell.preferencesOpen()).toBe(true);
    shell.closePreferences();
    expect(shell.preferencesOpen()).toBe(false);

    shell.openSecurity();
    expect(shell.securityOpen()).toBe(true);
    shell.closeSecurity();
    expect(shell.securityOpen()).toBe(false);
  });

  it('owns logout state instead of duplicating it in nested layouts', () => {
    const shell = TestBed.inject(AuthenticatedShellService);

    shell.logout();

    expect(auth.logout).toHaveBeenCalledOnce();
    expect(auth.finishLogout).toHaveBeenCalledOnce();
    expect(shell.loggingOut()).toBe(false);
    expect(shell.logoutError()).toBeNull();
  });

  it('exposes logout failures through the shared shell state', () => {
    auth.logout.mockReturnValueOnce(throwError(() => new Error('network')));
    const shell = TestBed.inject(AuthenticatedShellService);

    shell.logout();

    expect(shell.loggingOut()).toBe(false);
    expect(shell.logoutError()).toBe('logout error');
  });
});
