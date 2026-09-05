import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { catchError, finalize, of, switchMap, tap } from 'rxjs';
import { ApiErrorService } from '../../../core/api/api-error';
import { AuthService } from '../../../core/auth/auth.service';
import { I18nService } from '../../../core/i18n/i18n.service';
import { PreferenceDefaultsService } from '../../../core/preferences/preference-defaults.service';
import { PreferencesService } from '../../../core/preferences/preferences.service';
import {
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  OPTIONAL_TOTP_PATTERN,
  USER_NAME_MAX_LENGTH,
  USER_NAME_PATTERN,
} from '../../../shared/forms/backend-validators';
import { CrockfordCodeInputDirective, normalizeCrockfordCode } from '../../../shared/forms/crockford-code-input.directive';
import { NoWhitespaceInputDirective } from '../../../shared/forms/no-whitespace-input.directive';
import { AuthCardComponent } from '../../../shared/ui/auth-card.component';
import { AuthShellComponent } from '../../../shared/ui/auth-shell.component';
import { FieldErrorComponent } from '../../../shared/ui/field-error.component';
import { FormMessageComponent } from '../../../shared/ui/form-message.component';
import { IconComponent } from '../../../shared/ui/icon.component';
import { PasswordRecoveryDialogComponent } from '../password-recovery/password-recovery.component';

@Component({
  selector: 'app-auth-landing',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    CrockfordCodeInputDirective,
    NoWhitespaceInputDirective,
    AuthShellComponent,
    AuthCardComponent,
    FieldErrorComponent,
    IconComponent,
    FormMessageComponent,
    PasswordRecoveryDialogComponent,
  ],
  template: `
    <app-auth-shell>
      <section class="auth-layout">
        <app-auth-card [title]="i18n.t('auth.login.title')" icon="user" accent="green">
          <form class="login-form" [formGroup]="loginForm" (ngSubmit)="submitLogin()" novalidate>
            <label class="field">
              <span>{{ i18n.t('auth.username') }} <span class="required-mark" aria-hidden="true">*</span></span>
              <input appNoWhitespace autocomplete="username" formControlName="name" required />
              <app-field-error [text]="usernameError(loginForm.controls.name)" />
            </label>

            <label class="field">
              <span>{{ i18n.t('auth.password') }} <span class="required-mark" aria-hidden="true">*</span></span>
              <div class="input-with-action">
                <input appNoWhitespace [type]="showLoginPassword() ? 'text' : 'password'" autocomplete="current-password"
                  formControlName="password" required />
                <button type="button" class="icon-action" (click)="showLoginPassword.set(!showLoginPassword())"
                  [attr.aria-label]="showLoginPassword() ? i18n.t('auth.password.hide') : i18n.t('auth.password.show')">
                  <app-icon [name]="showLoginPassword() ? 'eye-off' : 'eye'" />
                </button>
              </div>
              <app-field-error [text]="passwordError(loginForm.controls.password)" />
            </label>

            <label class="field">
              <span>{{ i18n.t('auth.totp') }}</span>
              <input inputmode="numeric" autocomplete="one-time-code" formControlName="totp_code" maxlength="6" />
              <app-field-error [text]="totpError(loginForm.controls.totp_code)" />
            </label>

            <div class="login-options">
              <label class="checkbox"><input type="checkbox" formControlName="remember" /> <span>{{ i18n.t('auth.remember') }}</span></label>
              <button class="text-button" type="button" (click)="recoveryOpen.set(true)">{{ i18n.t('auth.forgotPassword') }}</button>
            </div>

            <div class="login-feedback" aria-live="polite">
              @if (loginError()) {
                <app-form-message [text]="loginError()!" />
              } @else if (passwordChanged()) {
                <app-form-message kind="success" [text]="i18n.t('auth.passwordChanged')" />
              }
            </div>

            <button class="ui-button ui-button--green ui-button--full" type="submit" [disabled]="loginForm.invalid || loadingLogin()">
              <span>{{ loadingLogin() ? i18n.t('auth.signingIn') : i18n.t('auth.signIn') }}</span>
              <app-icon name="arrow-right" />
            </button>
          </form>
        </app-auth-card>

        <app-auth-card [title]="i18n.t('auth.register.title')" icon="mail" accent="yellow">
          <form class="registration-form" [formGroup]="registrationForm" (ngSubmit)="submitRegistration()" (input)="registrationSuccess.set(false)" novalidate>
            <label class="field">
              <span>{{ i18n.t('auth.invite.label') }} <span class="required-mark" aria-hidden="true">*</span></span>
              <input appCrockfordCode formControlName="invitation_code" autocomplete="off" required />
              <app-field-error [text]="codeError(registrationForm.controls.invitation_code)" />
            </label>

            <label class="field">
              <span>{{ i18n.t('auth.username') }} <span class="required-mark" aria-hidden="true">*</span></span>
              <input appNoWhitespace formControlName="name" autocomplete="username" required />
              <app-field-error [text]="usernameError(registrationForm.controls.name)" />
            </label>

            <label class="field">
              <span>{{ i18n.t('auth.password') }} <span class="required-mark" aria-hidden="true">*</span></span>
              <div class="input-with-action">
                <input appNoWhitespace [type]="showRegistrationPassword() ? 'text' : 'password'" formControlName="password"
                  autocomplete="new-password" required />
                <button type="button" class="icon-action" (click)="showRegistrationPassword.set(!showRegistrationPassword())"
                  [attr.aria-label]="showRegistrationPassword() ? i18n.t('auth.password.hide') : i18n.t('auth.password.show')">
                  <app-icon [name]="showRegistrationPassword() ? 'eye-off' : 'eye'" />
                </button>
              </div>
              <app-field-error [text]="passwordError(registrationForm.controls.password)" />
            </label>

            <label class="field">
              <span>{{ i18n.t('auth.register.confirmPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
              <input appNoWhitespace type="password" formControlName="confirm_password" autocomplete="new-password" required />
              <app-field-error [text]="confirmPasswordError()" />
            </label>

            @if (registrationSuccess()) { <app-form-message kind="success" [text]="i18n.t('auth.register.success')" /> }
            @if (registrationError()) { <app-form-message [text]="registrationError()!" /> }

            <button class="ui-button ui-button--yellow ui-button--full" type="submit"
              [disabled]="registrationForm.invalid || passwordMismatch() || loadingRegistration()">
              <span>{{ loadingRegistration() ? i18n.t('auth.register.creating') : i18n.t('auth.register.title') }}</span>
              <app-icon name="arrow-right" />
            </button>
          </form>
        </app-auth-card>
      </section>

      <app-password-recovery-dialog [open]="recoveryOpen()" (close)="recoveryOpen.set(false)" />
    </app-auth-shell>
  `,
  styles: `
    .auth-layout { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: clamp(30px, 4.5vw, 54px); align-items: stretch; }
    app-auth-card { height: 100%; }
    form { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; gap: var(--form-gap); }
    .login-options { display: flex; justify-content: space-between; gap: var(--form-gap); align-items: center; margin: -2px 0 2px; font-size: .88rem; }
    .login-feedback {
      position: relative;
      flex: 1 1 64px;
      min-height: 0;
    }
    .login-feedback app-form-message {
      position: absolute;
      inset: auto 0 0;
      width: 100%;
    }
    .text-button { padding: 0; border: 0; background: transparent; color: var(--link); font: inherit; font-weight: 680; text-decoration: none; }
    .text-button:hover { text-decoration: underline; }
    form > .ui-button { margin-top: auto; }
    @media (max-width: 860px) {
      .auth-layout { grid-template-columns: 1fr; width: min(590px, 100%); margin: 0 auto; }
      .login-feedback { flex: 0 0 auto; min-height: 0; }
      .login-feedback app-form-message { position: static; display: block; width: auto; }
    }
    @media (max-width: 520px) {
      .login-options { align-items: flex-start; flex-direction: column; gap: var(--form-gap); margin: 0 0 2px; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthLandingComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly apiErrors = inject(ApiErrorService);
  private readonly preferences = inject(PreferencesService);
  private readonly preferenceDefaults = inject(PreferenceDefaultsService);
  readonly i18n = inject(I18nService);

  readonly showLoginPassword = signal(false);
  readonly showRegistrationPassword = signal(false);
  readonly loadingLogin = signal(false);
  readonly loadingRegistration = signal(false);
  readonly loginError = signal<string | null>(null);
  readonly registrationError = signal<string | null>(null);
  readonly registrationSuccess = signal(false);
  readonly passwordChanged = signal(history.state?.passwordChanged === true);
  readonly recoveryOpen = signal(false);

  readonly loginForm = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(USER_NAME_MAX_LENGTH), Validators.pattern(USER_NAME_PATTERN)]],
    password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH), Validators.maxLength(PASSWORD_MAX_LENGTH)]],
    remember: [false],
    totp_code: ['', Validators.pattern(OPTIONAL_TOTP_PATTERN)],
  });

  readonly registrationForm = this.fb.nonNullable.group({
    invitation_code: ['', Validators.required],
    name: ['', [Validators.required, Validators.maxLength(USER_NAME_MAX_LENGTH), Validators.pattern(USER_NAME_PATTERN)]],
    password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH), Validators.maxLength(PASSWORD_MAX_LENGTH)]],
    confirm_password: ['', [Validators.required, Validators.maxLength(PASSWORD_MAX_LENGTH)]],
  });

  constructor() {
    if (this.passwordChanged()) setTimeout(() => this.passwordChanged.set(false), 5000);
  }

  submitLogin(): void {
    if (this.loginForm.invalid || this.loadingLogin()) return;

    this.loadingLogin.set(true);
    this.loginError.set(null);
    const value = this.loginForm.getRawValue();
    this.auth.login({
      name: value.name,
      password: value.password,
      remember: value.remember,
      totp_code: value.totp_code.trim() || null,
    }).pipe(finalize(() => this.loadingLogin.set(false))).subscribe({
      next: () => void this.router.navigateByUrl('/home'),
      error: (error: unknown) => {
        // Invalid credentials/TOTP stay indistinguishable. A valid but already-used
        // TOTP code is actionable, so the backend exposes it separately.
        this.loginError.set(this.apiErrors.message(error, 'errors.loginFailed'));
      },
    });
  }

  submitRegistration(): void {
    if (this.registrationForm.invalid || this.passwordMismatch() || this.loadingRegistration()) return;

    this.loadingRegistration.set(true);
    this.registrationError.set(null);
    this.registrationSuccess.set(false);
    const value = this.registrationForm.getRawValue();
    const initialPreferences = this.preferenceDefaults.infer();
    let accountCreated = false;

    this.auth.register({
      invitation_code: normalizeCrockfordCode(value.invitation_code),
      name: value.name,
      password: value.password,
    }).pipe(
      tap(() => {
        accountCreated = true;
        this.registrationSuccess.set(true);
      }),
      // PUT /api/user/preferences is authenticated. After creating the account,
      // sign in normally with the credentials the user just supplied, persist
      // the browser-derived initial preferences, and keep that session as the
      // user's first signed-in session.
      switchMap(() => this.auth.login({
        name: value.name,
        password: value.password,
        remember: false,
        totp_code: null,
      })),
      switchMap(() => this.preferences.save(initialPreferences).pipe(
        // Preference initialization must not invalidate an account that was
        // already created and authenticated. /home will retry on a 404.
        catchError(() => of(initialPreferences)),
      )),
      finalize(() => this.loadingRegistration.set(false)),
    ).subscribe({
      next: () => {
        this.registrationForm.reset({ invitation_code: '', name: '', password: '', confirm_password: '' });
        this.showRegistrationPassword.set(false);
        void this.router.navigateByUrl('/home', { state: { accountCreated: true } });
      },
      error: (error: unknown) => {
        if (accountCreated) {
          // Registration itself succeeded, but the automatic first sign-in did
          // not. Keep the success state and prepare the regular login form.
          this.loginForm.controls.name.setValue(value.name);
          this.loginForm.controls.password.reset('');
          this.registrationForm.reset({ invitation_code: '', name: '', password: '', confirm_password: '' });
          this.showRegistrationPassword.set(false);
          return;
        }
        this.registrationError.set(this.apiErrors.message(error, 'errors.registrationFailed'));
      },
    });
  }

  passwordMismatch(): boolean {
    const { password, confirm_password } = this.registrationForm.getRawValue();
    return !!confirm_password && password !== confirm_password;
  }

  usernameError(control: AbstractControl): string | null {
    if (!this.shouldShowError(control)) return null;
    if (control.hasError('maxlength')) return this.i18n.t('validation.username.max', { max: USER_NAME_MAX_LENGTH });
    if (control.hasError('pattern')) return this.i18n.t('validation.username.characters');
    return null;
  }

  passwordError(control: AbstractControl): string | null {
    if (!this.shouldShowError(control)) return null;
    if (control.hasError('minlength')) return this.i18n.t('validation.password.min', { min: PASSWORD_MIN_LENGTH });
    if (control.hasError('maxlength')) return this.i18n.t('validation.password.max', { max: PASSWORD_MAX_LENGTH });
    return null;
  }

  codeError(control: AbstractControl): string | null {
    if (!this.shouldShowError(control)) return null;
    if (control.hasError('crockfordCode')) return this.i18n.t('validation.code.invalid');
    return null;
  }

  totpError(control: AbstractControl): string | null {
    if (!this.shouldShowError(control)) return null;
    if (control.hasError('pattern')) return this.i18n.t('validation.totp.invalid');
    return null;
  }

  confirmPasswordError(): string | null {
    const control = this.registrationForm.controls.confirm_password;
    if (!this.shouldShowError(control)) return null;
    if (control.hasError('maxlength')) return this.i18n.t('validation.password.max', { max: PASSWORD_MAX_LENGTH });
    if (this.passwordMismatch()) return this.i18n.t('auth.register.passwordMismatch');
    return null;
  }

  private shouldShowError(control: AbstractControl): boolean {
    return control.invalid && control.dirty;
  }
}
