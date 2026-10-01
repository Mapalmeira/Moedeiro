import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
import { AuthService } from './auth.service';

const routerStub = {
  navigateByUrl: vi.fn().mockResolvedValue(true),
};

describe('AuthService', () => {
  let service: AuthService;
  let http: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    routerStub.navigateByUrl.mockClear();

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: routerStub },
      ],
    });

    service = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('stores the username only after a successful login', () => {
    service.login({ name: 'alice', password: 'password123', remember: false, totp_code: null }).subscribe();

    expect(service.currentUserName()).toBeNull();
    expect(localStorage.getItem('moedeiro.last-auth-name')).toBeNull();

    const request = http.expectOne(API_ROUTES.authentication.login);
    request.flush(null);

    expect(service.authenticated()).toBe(true);
    expect(service.currentUserName()).toBe('alice');
    expect(localStorage.getItem('moedeiro.last-auth-name')).toBe('alice');
  });

  it('registers and recovers a password without mutating the session state', () => {
    const registration = { invitation_code: 'ABCDEFGHJKMNPQRS', name: 'alice', password: 'password123' };
    service.register(registration).subscribe();
    const registerRequest = http.expectOne(API_ROUTES.registration);
    expect(registerRequest.request.method).toBe('POST');
    expect(registerRequest.request.body).toEqual(registration);
    registerRequest.flush(null);

    const recovery = { name: 'alice', recovery_code: 'ABCDEFGHJKMNPQRS', new_password: 'replacement', totp_code: null };
    service.recoverPassword(recovery).subscribe();
    const recoveryRequest = http.expectOne(API_ROUTES.password.recovery);
    expect(recoveryRequest.request.method).toBe('POST');
    expect(recoveryRequest.request.body).toEqual(recovery);
    recoveryRequest.flush(null);

    expect(service.authenticated()).toBeNull();
  });

  it('accepts a valid existing session without rotating refresh credentials', () => {
    service.ensureSession().subscribe((valid) => expect(valid).toBe(true));
    http.expectOne(API_ROUTES.authentication.session).flush({ name: 'alice' });
    http.expectNone(API_ROUTES.authentication.refresh);

    expect(service.authenticated()).toBe(true);
    expect(service.currentUserName()).toBe('alice');
  });

  it('reuses a session established by login without immediately revalidating it', () => {
    service.login({ name: 'alice', password: 'password123', remember: false, totp_code: null }).subscribe();
    http.expectOne(API_ROUTES.authentication.login).flush(null);

    service.ensureSession().subscribe((valid) => expect(valid).toBe(true));

    http.expectNone(API_ROUTES.authentication.session);
  });

  it('uses refresh only when ensureSession receives a 401', () => {
    service.ensureSession().subscribe((valid) => expect(valid).toBe(true));

    http.expectOne(API_ROUTES.authentication.session).flush(null, { status: 401, statusText: 'Unauthorized' });
    http.expectOne(API_ROUTES.authentication.refresh).flush(null);
    http.expectOne(API_ROUTES.authentication.session).flush({ name: 'alice' });

    expect(service.authenticated()).toBe(true);
    expect(service.currentUserName()).toBe('alice');
  });

  it('shares one refresh request between concurrent refreshSession callers', () => {
    const first = vi.fn();
    const second = vi.fn();

    service.refreshSession().subscribe(first);
    service.refreshSession().subscribe(second);

    http.expectOne(API_ROUTES.authentication.refresh).flush(null);
    http.expectOne(API_ROUTES.authentication.session).flush({ name: 'alice' });

    expect(first).toHaveBeenCalledWith(true);
    expect(second).toHaveBeenCalledWith(true);
    expect(service.authenticated()).toBe(true);
  });

  it('does not try refresh for non-401 session failures', () => {
    localStorage.setItem('moedeiro.last-auth-name', 'stale');

    service.ensureSession().subscribe((valid) => expect(valid).toBe(false));

    http.expectOne(API_ROUTES.authentication.session).flush(null, { status: 503, statusText: 'Unavailable' });
    http.expectNone(API_ROUTES.authentication.refresh);

    expect(service.authenticated()).toBe(false);
    expect(service.currentUserName()).toBeNull();
    expect(localStorage.getItem('moedeiro.last-auth-name')).toBeNull();
  });

  it('clears local authentication when refresh cannot establish a session', () => {
    localStorage.setItem('moedeiro.last-auth-name', 'stale');
    service.currentUserName.set('stale');

    service.refreshSession().subscribe((valid) => expect(valid).toBe(false));
    http.expectOne(API_ROUTES.authentication.refresh).flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(service.authenticated()).toBe(false);
    expect(service.currentUserName()).toBeNull();
  });

  it('clears the cached username when logging out, including an already-expired session', () => {
    localStorage.setItem('moedeiro.last-auth-name', 'alice');
    service.currentUserName.set('alice');
    service.authenticated.set(true);

    service.logout().subscribe();
    http.expectOne(API_ROUTES.authentication.logout).flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(service.authenticated()).toBe(false);
    expect(service.currentUserName()).toBeNull();
    expect(localStorage.getItem('moedeiro.last-auth-name')).toBeNull();
  });

  it('clears local auth state before navigating after finishLogout', async () => {
    localStorage.setItem('moedeiro.last-auth-name', 'alice');
    service.currentUserName.set('alice');
    service.authenticated.set(true);

    await service.finishLogout({ passwordChanged: true });

    expect(service.authenticated()).toBe(false);
    expect(service.currentUserName()).toBeNull();
    expect(routerStub.navigateByUrl).toHaveBeenCalledWith('/', { state: { passwordChanged: true } });
  });
});
