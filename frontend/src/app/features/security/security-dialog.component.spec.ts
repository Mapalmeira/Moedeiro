import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';
import { I18nService } from '../../core/i18n/i18n.service';
import { SecurityService } from '../../core/security/security.service';
import { SecurityDialogComponent } from './security-dialog.component';

describe('SecurityDialogComponent', () => {
  const totpStatus = signal<'unknown' | 'DISABLED' | 'PENDING' | 'ENABLED'>('DISABLED');
  const security = {
    totpStatus: totpStatus.asReadonly(),
    getTotpStatus: vi.fn(() => of({ state: 'DISABLED' as const, provisioning_uri: null, expires_at: null })),
    changePassword: vi.fn(),
    startTotpSetup: vi.fn(),
    confirmTotp: vi.fn(),
    disableTotp: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    totpStatus.set('DISABLED');
    security.getTotpStatus.mockReturnValue(of({ state: 'DISABLED', provisioning_uri: null, expires_at: null }));
    security.changePassword.mockReturnValue(of(void 0));
    security.startTotpSetup.mockReturnValue(of({ state: 'PENDING', provisioning_uri: 'otpauth://totp/Moedeiro?secret=ABC123', expires_at: Math.floor(Date.now() / 1000) + 60 }));
    security.confirmTotp.mockReturnValue(of(void 0));
    security.disableTotp.mockReturnValue(of(void 0));
    TestBed.configureTestingModule({
      providers: [
        { provide: SecurityService, useValue: security },
        { provide: AuthService, useValue: { finishLogout: vi.fn() } },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'error') } },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
  });

  it('clears transient setup state before closing', () => {
    const component = TestBed.runInInjectionContext(() => new SecurityDialogComponent());
    const closed = vi.fn();
    component.close.subscribe(closed);
    component.provisioningUri.set('otpauth://totp/Moedeiro?secret=ABC123');
    component.totpSecret.set('ABC123');
    component.qrDataUrl.set('data:image/png;base64,test');
    component.secretCopied.set(true);
    component.secretVisible.set(true);
    component.confirmTotpForm.controls.code.setValue('123456');

    component.requestClose();

    expect(component.provisioningUri()).toBeNull();
    expect(component.totpSecret()).toBe('');
    expect(component.qrDataUrl()).toBeNull();
    expect(component.secretCopied()).toBe(false);
    expect(component.secretVisible()).toBe(false);
    expect(component.confirmTotpForm.controls.code.value).toBe('');
    expect(closed).toHaveBeenCalledOnce();
  });

  it('does not close while a security mutation is active', () => {
    const component = TestBed.runInInjectionContext(() => new SecurityDialogComponent());
    const closed = vi.fn();
    component.close.subscribe(closed);
    component.confirmingTotp.set(true);

    component.requestClose();

    expect(closed).not.toHaveBeenCalled();
  });

  it('changes the password and finishes the authenticated session', () => {
    const component = TestBed.runInInjectionContext(() => new SecurityDialogComponent());
    const auth = TestBed.inject(AuthService);
    component.passwordForm.setValue({ current_password: 'current password', new_password: 'replacement password', confirm_password: 'replacement password', totp_code: '' });

    component.changePassword();

    expect(security.changePassword).toHaveBeenCalledWith({ current_password: 'current password', new_password: 'replacement password', totp_code: null });
    expect(auth.finishLogout).toHaveBeenCalledWith({ passwordChanged: true });
    expect(component.changingPassword()).toBe(false);
  });

  it('uses temporary field feedback for rejected password credentials', () => {
    security.changePassword.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 401, error: { detail: 'Invalid current password' } })));
    const component = TestBed.runInInjectionContext(() => new SecurityDialogComponent());
    component.passwordForm.setValue({ current_password: 'current password', new_password: 'replacement password', confirm_password: 'replacement password', totp_code: '' });

    component.changePassword();

    expect(component.passwordCurrentFeedback()).toBe('errors.invalidCurrentPassword');
    expect(component.passwordErrorMessage()).toBeNull();
  });

  it('starts a pending TOTP setup and exposes its secret and expiry', () => {
    const component = TestBed.runInInjectionContext(() => new SecurityDialogComponent());
    component.setupForm.setValue({ current_password: 'current password' });

    component.startTotpSetup();

    expect(security.startTotpSetup).toHaveBeenCalledWith({ current_password: 'current password' });
    expect(component.provisioningUri()).toContain('secret=ABC123');
    expect(component.totpSecret()).toBe('ABC123');
    expect(component.setupSecondsRemaining()).toBeGreaterThan(0);
    component.requestClose();
  });

  it('rejects malformed setup responses without retaining provisioning state', () => {
    security.startTotpSetup.mockReturnValue(of({ state: 'DISABLED', provisioning_uri: null, expires_at: null }));
    const component = TestBed.runInInjectionContext(() => new SecurityDialogComponent());
    component.setupForm.setValue({ current_password: 'current password' });

    component.startTotpSetup();

    expect(component.totpErrorMessage()).toBe('errors.totpSetupFailed');
    expect(component.provisioningUri()).toBeNull();
  });

  it('confirms and disables TOTP while clearing sensitive form state', () => {
    const component = TestBed.runInInjectionContext(() => new SecurityDialogComponent());
    component.confirmTotpForm.setValue({ code: '123456' });
    component.provisioningUri.set('otpauth://setup');
    component.totpSecret.set('ABC123');
    component.confirmTotp();

    expect(security.confirmTotp).toHaveBeenCalledWith({ code: '123456' });
    expect(component.provisioningUri()).toBeNull();
    expect(component.totpSecret()).toBe('');
    expect(component.totpInfoMessage()).toBe('security.totp.enabled');

    totpStatus.set('ENABLED');
    component.disableTotpForm.setValue({ current_password: 'current password', code: '654321' });
    component.disableTotp();
    expect(security.disableTotp).toHaveBeenCalledWith({ current_password: 'current password', code: '654321' });
    expect(component.totpSuccessMessage()).toBe('security.totp.disabled');
  });

  it('reports a TOTP status load failure and allows retrying', () => {
    security.getTotpStatus.mockReturnValue(throwError(() => new Error('offline')));
    const component = TestBed.runInInjectionContext(() => new SecurityDialogComponent());

    component.loadTotpStatus();

    expect(component.totpStatusErrorMessage()).toBe('error');
    expect(component.loadingTotpStatus()).toBe(false);
  });
});
