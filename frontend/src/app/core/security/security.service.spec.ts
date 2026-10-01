import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
import { SecurityService } from './security.service';

describe('SecurityService', () => {
  let service: SecurityService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(SecurityService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('changes the password with the complete credential payload', () => {
    const payload = { current_password: 'current', new_password: 'replacement', totp_code: '123456' };
    service.changePassword(payload).subscribe();
    const request = http.expectOne(API_ROUTES.password.change);

    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(payload);
    request.flush(null);
  });

  it('marks TOTP unknown while refreshing and publishes the response state', () => {
    service.totpStatus.set('ENABLED');
    service.getTotpStatus().subscribe();
    expect(service.totpStatus()).toBe('unknown');

    http.expectOne(API_ROUTES.totp.root).flush({ state: 'PENDING', provisioning_uri: 'otpauth://setup', expires_at: 20 });
    expect(service.totpStatus()).toBe('PENDING');
  });

  it('starts setup without changing the confirmed TOTP state', () => {
    service.totpStatus.set('DISABLED');
    service.startTotpSetup({ current_password: 'password' }).subscribe();
    const request = http.expectOne(API_ROUTES.totp.setup);

    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ current_password: 'password' });
    request.flush({ state: 'PENDING', provisioning_uri: 'otpauth://setup', expires_at: 20 });
    expect(service.totpStatus()).toBe('DISABLED');
  });

  it('marks TOTP enabled only after confirmation succeeds', () => {
    service.totpStatus.set('PENDING');
    service.confirmTotp({ code: '123456' }).subscribe();
    expect(service.totpStatus()).toBe('PENDING');

    http.expectOne(API_ROUTES.totp.confirm).flush(null);
    expect(service.totpStatus()).toBe('ENABLED');
  });

  it('sends disable credentials in the delete body and publishes the new state', () => {
    const payload = { current_password: 'password', code: '123456' };
    service.totpStatus.set('ENABLED');
    service.disableTotp(payload).subscribe();
    const request = http.expectOne(API_ROUTES.totp.root);

    expect(request.request.method).toBe('DELETE');
    expect(request.request.body).toEqual(payload);
    request.flush(null);
    expect(service.totpStatus()).toBe('DISABLED');
  });
});
