import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
import { AuthService } from './auth.service';
import { sessionRefreshInterceptor } from './session-refresh.interceptor';

const routerStub = {
  navigateByUrl: vi.fn().mockResolvedValue(true),
};

describe('sessionRefreshInterceptor', () => {
  let client: HttpClient;
  let http: HttpTestingController;
  let auth: AuthService;

  beforeEach(() => {
    localStorage.clear();
    routerStub.navigateByUrl.mockClear();

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([sessionRefreshInterceptor])),
        provideHttpClientTesting(),
        { provide: Router, useValue: routerStub },
      ],
    });

    client = TestBed.inject(HttpClient);
    http = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
  });

  afterEach(() => http.verify());

  it('refreshes an expired remembered session and retries the protected request', () => {
    const received = vi.fn();
    client.get('/api/protected').subscribe(received);

    http.expectOne('/api/protected').flush(
      { detail: 'Invalid session' },
      { status: 401, statusText: 'Unauthorized' },
    );
    http.expectOne(API_ROUTES.authentication.refresh).flush(null);
    http.expectOne(API_ROUTES.authentication.session).flush({ name: 'alice' });
    http.expectOne('/api/protected').flush({ ok: true });

    expect(received).toHaveBeenCalledWith({ ok: true });
    expect(auth.authenticated()).toBe(true);
    expect(auth.currentUserName()).toBe('alice');
    expect(routerStub.navigateByUrl).not.toHaveBeenCalled();
  });

  it('shares one rotating remember-token refresh across concurrent expired requests', () => {
    const first = vi.fn();
    const second = vi.fn();
    client.get('/api/first').subscribe(first);
    client.get('/api/second').subscribe(second);

    http.expectOne('/api/first').flush(
      { detail: 'Invalid session' },
      { status: 401, statusText: 'Unauthorized' },
    );
    http.expectOne('/api/second').flush(
      { detail: 'Invalid session' },
      { status: 401, statusText: 'Unauthorized' },
    );

    http.expectOne(API_ROUTES.authentication.refresh).flush(null);
    http.expectOne(API_ROUTES.authentication.session).flush({ name: 'alice' });
    http.expectOne('/api/first').flush({ id: 1 });
    http.expectOne('/api/second').flush({ id: 2 });

    expect(first).toHaveBeenCalledWith({ id: 1 });
    expect(second).toHaveBeenCalledWith({ id: 2 });
    expect(http.match(API_ROUTES.authentication.refresh)).toHaveLength(0);
  });

  it('does not treat another 401 meaning as an expired session', () => {
    const error = vi.fn();
    client.get('/api/protected').subscribe({ error });

    http.expectOne('/api/protected').flush(
      { detail: 'Invalid credentials' },
      { status: 401, statusText: 'Unauthorized' },
    );

    http.expectNone(API_ROUTES.authentication.refresh);
    expect(error).toHaveBeenCalledOnce();
  });
});
