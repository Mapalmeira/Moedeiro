import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../core/api/api-error';
import { AuthService } from '../../../core/auth/auth.service';
import { I18nService } from '../../../core/i18n/i18n.service';
import { PasswordRecoveryDialogComponent } from './password-recovery.component';

describe('PasswordRecoveryDialogComponent', () => {
  const auth = { recoverPassword: vi.fn(() => of(void 0)) };
  const apiErrors = { message: vi.fn(() => 'recovery failed') };
  let fixture: ComponentFixture<PasswordRecoveryDialogComponent>;

  beforeEach(() => {
    vi.clearAllMocks();
    auth.recoverPassword.mockReturnValue(of(void 0));
    TestBed.configureTestingModule({
      imports: [PasswordRecoveryDialogComponent],
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: ApiErrorService, useValue: apiErrors },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
    fixture = TestBed.createComponent(PasswordRecoveryDialogComponent);
    fixture.componentRef.setInput('open', true);
    fixture.detectChanges();
  });

  function fillValidForm(): void {
    fixture.componentInstance.form.setValue({
      name: 'alice', recovery_code: 'abcd-efgh-jkmn-pqrs', new_password: 'new password', confirm_password: 'new password', totp_code: '',
    });
  }

  it('normalizes credentials and completes only after recovery succeeds', () => {
    fillValidForm();
    fixture.componentInstance.submit();

    expect(auth.recoverPassword).toHaveBeenCalledWith({
      name: 'alice', recovery_code: 'ABCDEFGHJKMNPQRS', new_password: 'new password', totp_code: null,
    });
    expect(fixture.componentInstance.completed()).toBe(true);
    expect(fixture.componentInstance.form.disabled).toBe(true);
    expect(fixture.componentInstance.successMessage()).toBe('auth.recovery.success');
  });

  it('requires TOTP after the backend reports a stale enrollment state', () => {
    auth.recoverPassword.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 401, error: { detail: 'TOTP required' } })));
    fillValidForm();

    fixture.componentInstance.submit();

    expect(fixture.componentInstance.totpRequired()).toBe(true);
    expect(fixture.componentInstance.totpRequiredFeedback()).toBe('errors.totpRequired');
    expect(fixture.componentInstance.form.controls.totp_code.hasError('required')).toBe(true);
  });

  it('uses field feedback for rejected credentials and a message for other failures', () => {
    auth.recoverPassword.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 401, error: { detail: 'Invalid credentials' } })));
    fillValidForm();
    fixture.componentInstance.submit();
    expect(fixture.componentInstance.recoveryCredentialsFeedback()).toBe('errors.recoveryFailed');

    auth.recoverPassword.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 503 })));
    fixture.componentInstance.submit();
    expect(fixture.componentInstance.errorMessage()).toBe('recovery failed');
    expect(apiErrors.message).toHaveBeenCalledWith(expect.anything(), 'errors.recoveryFailed');
  });

  it('does not submit mismatched passwords and does not close while loading', () => {
    fillValidForm();
    fixture.componentInstance.form.controls.confirm_password.setValue('different');
    fixture.componentInstance.submit();
    expect(auth.recoverPassword).not.toHaveBeenCalled();

    const closed = vi.fn();
    fixture.componentInstance.close.subscribe(closed);
    fixture.componentInstance.loading.set(true);
    fixture.componentInstance.requestClose();
    expect(closed).not.toHaveBeenCalled();
  });

  it('resets transient state whenever the dialog opens', () => {
    fixture.componentInstance.completed.set(true);
    fixture.componentInstance.errorMessage.set('old');
    fixture.componentInstance.showPassword.set(true);
    fixture.componentInstance.form.disable();

    fixture.componentInstance.ngOnChanges();

    expect(fixture.componentInstance.completed()).toBe(false);
    expect(fixture.componentInstance.errorMessage()).toBeNull();
    expect(fixture.componentInstance.showPassword()).toBe(false);
    expect(fixture.componentInstance.form.enabled).toBe(true);
  });
});
