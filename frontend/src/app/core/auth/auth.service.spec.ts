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
    expect(request.request.withCredentials).toBe(true);
    request.flush(null);

    expect(service.authenticated()).toBe(true);
    expect(service.currentUserName()).toBe('alice');
    expect(localStorage.getItem('moedeiro.last-auth-name')).toBe('alice');
  });

  it('reuses a session established by login without immediately revalidating it', () => {
    service.login({ name: 'alice', password: 'password123', remember: false, totp_code: null }).subscribe();
    http.expectOne(API_ROUTES.authentication.login).flush(null);

    service.ensureSession().subscribe((valid) => expect(valid).toBe(true));

    http.expectNone(API_ROUTES.authentication.session);
  });

  it('refreshes the stored username when validating the session', () => {
    service.validateSession().subscribe((valid) => expect(valid).toBe(true));

    http.expectOne(API_ROUTES.authentication.session).flush({ name: 'server-name' });

    expect(service.authenticated()).toBe(true);
    expect(service.currentUserName()).toBe('server-name');
    expect(localStorage.getItem('moedeiro.last-auth-name')).toBe('server-name');
  });

  it('uses refresh only when ensureSession receives a 401', () => {
    service.ensureSession().subscribe((valid) => expect(valid).toBe(true));

    http.expectOne(API_ROUTES.authentication.session).flush(null, { status: 401, statusText: 'Unauthorized' });
    http.expectOne(API_ROUTES.authentication.refresh).flush(null);
    http.expectOne(API_ROUTES.authentication.session).flush({ name: 'alice' });

    expect(service.authenticated()).toBe(true);
    expect(service.currentUserName()).toBe('alice');
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
