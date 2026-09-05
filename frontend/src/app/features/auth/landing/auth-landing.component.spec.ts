import { FormBuilder } from '@angular/forms';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../core/api/api-error';
import { AuthService } from '../../../core/auth/auth.service';
import { I18nService } from '../../../core/i18n/i18n.service';
import { AuthLandingComponent } from './auth-landing.component';

describe('AuthLandingComponent registration', () => {
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
    expect(component.registrationSuccess()).toBe(true);
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
    expect(component.registrationSuccess()).toBe(false);
    expect(component.registrationError()).toBe('registration failed');
    expect(component.loadingRegistration()).toBe(false);
  });
});
