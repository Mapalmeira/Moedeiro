import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
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
});
