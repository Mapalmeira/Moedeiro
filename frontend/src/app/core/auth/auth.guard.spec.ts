import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthService } from './auth.service';
import { authGuard, guestGuard } from './auth.guard';

describe('authentication guards', () => {
  const auth = { ensureSession: vi.fn() };
  const landingRedirect = { path: '/' };
  const homeRedirect = { path: '/home' };
  const router = {
    createUrlTree: vi.fn((segments: string[]) => segments[0] === '/' ? landingRedirect : homeRedirect),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: Router, useValue: router },
      ],
    });
  });

  it('allows an authenticated user into protected routes', () => {
    auth.ensureSession.mockReturnValue(of(true));
    const result = TestBed.runInInjectionContext(() => authGuard(null!, null!));

    (result as ReturnType<typeof of>).subscribe((value) => expect(value).toBe(true));
  });

  it('redirects an unauthenticated user to the landing page', () => {
    auth.ensureSession.mockReturnValue(of(false));
    const result = TestBed.runInInjectionContext(() => authGuard(null!, null!));

    (result as ReturnType<typeof of>).subscribe((value) => expect(value).toBe(landingRedirect));
    expect(router.createUrlTree).toHaveBeenCalledWith(['/']);
  });

  it('allows a guest into public authentication routes', () => {
    auth.ensureSession.mockReturnValue(of(false));
    const result = TestBed.runInInjectionContext(() => guestGuard(null!, null!));

    (result as ReturnType<typeof of>).subscribe((value) => expect(value).toBe(true));
  });

  it('redirects an authenticated user away from guest routes', () => {
    auth.ensureSession.mockReturnValue(of(true));
    const result = TestBed.runInInjectionContext(() => guestGuard(null!, null!));

    (result as ReturnType<typeof of>).subscribe((value) => expect(value).toBe(homeRedirect));
    expect(router.createUrlTree).toHaveBeenCalledWith(['/home']);
  });
});
