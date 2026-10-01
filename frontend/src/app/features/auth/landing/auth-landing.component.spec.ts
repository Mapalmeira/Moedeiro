import { FormBuilder } from '@angular/forms';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../core/api/api-error';
import { AuthService } from '../../../core/auth/auth.service';
import { I18nService } from '../../../core/i18n/i18n.service';
import { AuthLandingComponent } from './auth-landing.component';

describe('AuthLandingComponent', () => {
  const auth = {
    register: vi.fn(),
    login: vi.fn(),
  };
  const router = {
    navigateByUrl: vi.fn(),
  };
  const apiErrors = {
    message: vi.fn(() => 'registration failed'),
  };
  const i18n = {
    t: vi.fn((key: string) => key),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        FormBuilder,
        { provide: AuthService, useValue: auth },
        { provide: Router, useValue: router },
        { provide: ApiErrorService, useValue: apiErrors },
        { provide: I18nService, useValue: i18n },
      ],
    });
  });

  function createComponent(): AuthLandingComponent {
    return TestBed.runInInjectionContext(() => new AuthLandingComponent());
  }

  function fillValidRegistration(component: AuthLandingComponent): void {
    component.registrationForm.setValue({
      invitation_code: 'ABCD-EFGH-JKMN-PQRS',
      name: 'alice',
      password: 'password123',
      confirm_password: 'password123',
    });
  }

  function fillValidLogin(component: AuthLandingComponent): void {
    component.loginForm.setValue({ name: 'alice', password: 'password123', remember: true, totp_code: '' });
  }

  it('logs in with normalized optional TOTP and navigates only after success', () => {
    auth.login.mockReturnValue(of(void 0));
    const component = createComponent();
    fillValidLogin(component);

    component.submitLogin();

    expect(auth.login).toHaveBeenCalledWith({ name: 'alice', password: 'password123', remember: true, totp_code: null });
    expect(router.navigateByUrl).toHaveBeenCalledWith('/home');
    expect(component.loadingLogin()).toBe(false);
  });

  it('keeps invalid credentials indistinguishable in field feedback', () => {
    auth.login.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 401, error: { detail: 'Invalid credentials' } })));
    const component = createComponent();
    fillValidLogin(component);

    component.submitLogin();

    expect(component.loginCredentialsFeedback()).toBe('errors.loginFailed');
    expect(component.loginError()).toBeNull();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it('requires a valid TOTP code when the backend reports it as required', () => {
    auth.login.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 401, error: { detail: 'TOTP required' } })));
    const component = createComponent();
    fillValidLogin(component);

    component.submitLogin();

    expect(component.loginCredentialsFeedback()).toBe('errors.totpRequired');
    expect(component.loginForm.controls.totp_code.hasError('required')).toBe(true);
    component.loginForm.controls.totp_code.setValue('123456');
    expect(component.loginForm.controls.totp_code.valid).toBe(true);
  });

  it('creates the account without automatically logging in or navigating', () => {
    auth.register.mockReturnValue(of(void 0));
    const component = createComponent();
    fillValidRegistration(component);

    component.submitRegistration();

    expect(auth.register).toHaveBeenCalledWith({
      invitation_code: 'ABCDEFGHJKMNPQRS',
      name: 'alice',
      password: 'password123',
    });
    expect(auth.login).not.toHaveBeenCalled();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
    expect(component.registrationCompleted()).toBe(true);
    expect(component.loginForm.controls.name.value).toBe('alice');
    expect(component.loginForm.controls.password.value).toBe('');
    expect(component.registrationForm.getRawValue()).toEqual({
      invitation_code: '',
      name: '',
      password: '',
      confirm_password: '',
    });
  });

  it('keeps the registration failure on the registration form without attempting login', () => {
    auth.register.mockReturnValue(throwError(() => new Error('boom')));
    const component = createComponent();
    fillValidRegistration(component);

    component.submitRegistration();

    expect(auth.login).not.toHaveBeenCalled();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
    expect(component.registrationCompleted()).toBe(false);
    expect(component.registrationError()).toBe('registration failed');
    expect(component.loadingRegistration()).toBe(false);
  });

  it('uses invitation feedback when registration races with invitation consumption', () => {
    auth.register.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 404, error: { detail: 'Invitation not available' } })));
    const component = createComponent();
    fillValidRegistration(component);

    component.submitRegistration();

    expect(component.registrationInvitationFeedback()).toBe('errors.invitationUnavailable');
    expect(component.registrationError()).toBeNull();
  });
});
import { HttpErrorResponse } from '@angular/common/http';
