import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../../core/api/api-error';
import { AuthService } from '../../../core/auth/auth.service';
import { I18nService } from '../../../core/i18n/i18n.service';
import {
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  OPTIONAL_TOTP_PATTERN,
  TOTP_PATTERN,
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
        <app-auth-card [title]="i18n.t('auth.login.title')" icon="LucideUser" accent="green">
          <form class="login-form" [formGroup]="loginForm" (ngSubmit)="submitLogin()" novalidate>
            <label class="field" [class.ui-field-feedback--rejected]="loginCredentialsRejected()">
              <span>{{ i18n.t('auth.username') }} <span class="required-mark" aria-hidden="true">*</span></span>
              <input appNoWhitespace autocomplete="username" formControlName="name" required (input)="clearLoginCredentialsRejection()" (animationend)="clearLoginCredentialsRejection()" [attr.aria-invalid]="loginCredentialsRejected()" [attr.aria-describedby]="loginCredentialsRejected() ? 'login-credentials-feedback' : null" />
              <app-field-error [text]="usernameError(loginForm.controls.name)" />
            </label>

            <label class="field" [class.ui-field-feedback--rejected]="loginCredentialsRejected()">
              <span>{{ i18n.t('auth.password') }} <span class="required-mark" aria-hidden="true">*</span></span>
              <div class="input-with-action">
                <input appNoWhitespace [type]="showLoginPassword() ? 'text' : 'password'" autocomplete="current-password"
                  formControlName="password" required (input)="clearLoginCredentialsRejection()" (animationend)="clearLoginCredentialsRejection()" [attr.aria-invalid]="loginCredentialsRejected()" [attr.aria-describedby]="loginCredentialsRejected() ? 'login-credentials-feedback' : null" />
                <button type="button" class="icon-action" (click)="showLoginPassword.set(!showLoginPassword())"
                  [attr.aria-label]="showLoginPassword() ? i18n.t('auth.password.hide') : i18n.t('auth.password.show')">
                  <app-icon [name]="showLoginPassword() ? 'LucideEyeOff' : 'LucideEye'" />
                </button>
              </div>
              <app-field-error [text]="passwordError(loginForm.controls.password)" />
            </label>

            <label class="field" [class.ui-field-feedback--rejected]="loginCredentialsRejected() || loginTotpRequired()">
              <span>{{ i18n.t('auth.totp') }}</span>
              <input inputmode="numeric" autocomplete="one-time-code" formControlName="totp_code" maxlength="6" (input)="clearLoginCredentialsRejection(); clearLoginTotpRequired()" (animationend)="clearLoginCredentialsRejection(); clearLoginTotpRequired()" [attr.aria-invalid]="loginCredentialsRejected() || loginTotpRequired()" [attr.aria-describedby]="loginCredentialsRejected() || loginTotpRequired() ? 'login-credentials-feedback' : null" />
              <app-field-error [text]="totpError(loginForm.controls.totp_code)" />
            </label>

            <div class="login-options">
              <label class="checkbox">
                <input class="checkbox__input ui-visually-hidden" type="checkbox" formControlName="remember" />
                <span class="checkbox__control ui-icon-badge" aria-hidden="true"><app-icon name="LucideCheck" size="indicator" /></span>
                <span>{{ i18n.t('auth.remember') }}</span>
              </label>
              <button class="text-button" type="button" (click)="recoveryOpen.set(true)">{{ i18n.t('auth.forgotPassword') }}</button>
            </div>

            <div class="login-feedback" aria-live="polite">
              @if (loginError()) {
                <app-form-message [text]="loginError()!" />
              } @else if (passwordChanged()) {
                <app-form-message kind="success" [text]="i18n.t('auth.passwordChanged')" />
              }
              <app-field-error messageId="login-credentials-feedback" [visuallyHidden]="true" [text]="loginCredentialsFeedback()" />
            </div>

            <button class="ui-button ui-button--green ui-button--full" type="submit" [disabled]="loginForm.invalid || loadingLogin()">
              <span>{{ i18n.t('auth.signIn') }}</span>
              <app-icon name="LucideArrowRight" />
            </button>
          </form>
        </app-auth-card>

        <app-auth-card [title]="i18n.t('auth.register.title')" icon="LucideMail" accent="yellow">
          <form class="registration-form" [formGroup]="registrationForm" (ngSubmit)="submitRegistration()" novalidate>
            <label class="field" [class.ui-field-feedback--rejected]="registrationInvitationRejected()">
              <span>{{ i18n.t('auth.invite.label') }} <span class="required-mark" aria-hidden="true">*</span></span>
              <input appCrockfordCode formControlName="invitation_code" autocomplete="off" required (input)="clearRegistrationInvitationRejection()" (animationend)="clearRegistrationInvitationRejection()" [attr.aria-invalid]="registrationInvitationRejected()" [attr.aria-describedby]="registrationInvitationRejected() ? 'registration-invitation-feedback' : null" />
              <app-field-error [text]="codeError(registrationForm.controls.invitation_code)" />
              <app-field-error messageId="registration-invitation-feedback" [visuallyHidden]="true" [text]="registrationInvitationFeedback()" />
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
                  <app-icon [name]="showRegistrationPassword() ? 'LucideEyeOff' : 'LucideEye'" />
                </button>
              </div>
              <app-field-error [text]="passwordError(registrationForm.controls.password)" />
            </label>

            <label class="field">
              <span>{{ i18n.t('auth.register.confirmPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
              <input appNoWhitespace type="password" formControlName="confirm_password" autocomplete="new-password" required />
              <app-field-error [text]="confirmPasswordError()" />
            </label>

            @if (registrationError()) { <app-form-message [text]="registrationError()!" /> }

            <button class="ui-button ui-button--yellow ui-button--full" type="submit"
              [disabled]="registrationForm.invalid || passwordMismatch() || loadingRegistration() || registrationCompleted()">
              <span>{{ i18n.t('auth.register.title') }}</span>
              <app-icon [name]="registrationCompleted() ? 'LucideCheck' : 'LucideArrowRight'" />
            </button>
          </form>
        </app-auth-card>
      </section>

      <app-password-recovery-dialog [open]="recoveryOpen()" (close)="recoveryOpen.set(false)" />
    </app-auth-shell>
  `,
  styles: `
    .auth-layout { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: clamp(30px, 4.5vw, 54px); align-items: stretch; }
    form { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; gap: var(--form-gap); }
    .login-options { display: flex; justify-content: space-between; gap: var(--form-gap); align-items: center; margin: 0; font-size: .88rem; }
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
  private readonly destroyRef = inject(DestroyRef);
  readonly i18n = inject(I18nService);

  readonly showLoginPassword = signal(false);
  readonly showRegistrationPassword = signal(false);
  readonly loadingLogin = signal(false);
  readonly loadingRegistration = signal(false);
  readonly loginError = signal<string | null>(null);
  readonly loginCredentialsRejected = signal(false);
  readonly loginTotpRequired = signal(false);
  readonly registrationError = signal<string | null>(null);
  readonly registrationInvitationRejected = signal(false);
  readonly registrationCompleted = signal(false);
  readonly passwordChanged = signal(history.state?.passwordChanged === true);
  readonly recoveryOpen = signal(false);
  private registrationCompletionTimer: ReturnType<typeof setTimeout> | null = null;
  private passwordChangedTimer: ReturnType<typeof setTimeout> | null = null;

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
    if (this.passwordChanged()) this.passwordChangedTimer = setTimeout(() => this.passwordChanged.set(false), 5_000);
    this.destroyRef.onDestroy(() => {
      if (this.passwordChangedTimer !== null) clearTimeout(this.passwordChangedTimer);
      if (this.registrationCompletionTimer !== null) clearTimeout(this.registrationCompletionTimer);
    });
  }

  submitLogin(): void {
    if (this.loginForm.invalid || this.loadingLogin()) return;

    this.loadingLogin.set(true);
    this.loginError.set(null);
    this.clearLoginCredentialsRejection();
    this.clearLoginTotpRequired();
    const value = this.loginForm.getRawValue();
    this.auth.login({
      name: value.name,
      password: value.password,
      remember: value.remember,
      totp_code: value.totp_code.trim() || null,
    }).pipe(finalize(() => this.loadingLogin.set(false))).subscribe({
      next: () => void this.router.navigateByUrl('/home'),
      error: (error: unknown) => {
        // Credential/TOTP failures remain indistinguishable, so reject the
        // credential set without exposing which value was rejected.
        if (this.hasErrorDetail(error, 'Invalid credentials')) this.loginCredentialsRejected.set(true);
        else if (this.hasErrorDetail(error, 'TOTP required')) {
          this.loginTotpRequired.set(true);
          this.loginForm.controls.totp_code.setValidators([Validators.required, Validators.pattern(TOTP_PATTERN)]);
          this.loginForm.controls.totp_code.updateValueAndValidity();
        }
        else this.loginError.set(this.apiErrors.message(error, 'errors.loginFailed'));
      },
    });
  }

  clearLoginCredentialsRejection(): void {
    this.loginCredentialsRejected.set(false);
  }

  loginCredentialsFeedback(): string | null {
    if (this.loginTotpRequired()) return this.i18n.t('errors.totpRequired');
    return this.loginCredentialsRejected() ? this.i18n.t('errors.loginFailed') : null;
  }

  clearLoginTotpRequired(): void {
    this.loginTotpRequired.set(false);
  }

  clearRegistrationInvitationRejection(): void {
    this.registrationInvitationRejected.set(false);
  }

  registrationInvitationFeedback(): string | null {
    return this.registrationInvitationRejected() ? this.i18n.t('errors.invitationUnavailable') : null;
  }

  private hasErrorDetail(error: unknown, detail: string): boolean {
    return error instanceof HttpErrorResponse && error.error?.detail === detail;
  }

  submitRegistration(): void {
    if (this.registrationForm.invalid || this.passwordMismatch() || this.loadingRegistration()) return;

    this.loadingRegistration.set(true);
    this.registrationError.set(null);
    this.clearRegistrationInvitationRejection();
    this.clearRegistrationCompletion();
    const value = this.registrationForm.getRawValue();

    this.auth.register({
      invitation_code: normalizeCrockfordCode(value.invitation_code),
      name: value.name,
      password: value.password,
    }).pipe(finalize(() => this.loadingRegistration.set(false))).subscribe({
      next: () => {
        // Registration only creates the account. Authentication remains an
        // explicit user action through the login form.
        this.loginForm.controls.name.setValue(value.name);
        this.loginForm.controls.password.reset('');
        this.registrationForm.reset({ invitation_code: '', name: '', password: '', confirm_password: '' });
        this.showRegistrationPassword.set(false);
        this.registrationCompleted.set(true);
        this.registrationCompletionTimer = setTimeout(() => this.clearRegistrationCompletion(), 2_000);
      },
      error: (error: unknown) => {
        if (this.hasErrorDetail(error, 'Invitation not available')) this.registrationInvitationRejected.set(true);
        else this.registrationError.set(this.apiErrors.message(error, 'errors.registrationFailed'));
      },
    });
  }

  passwordMismatch(): boolean {
    const { password, confirm_password } = this.registrationForm.getRawValue();
    return !!confirm_password && password !== confirm_password;
  }

  private clearRegistrationCompletion(): void {
    if (this.registrationCompletionTimer !== null) {
      clearTimeout(this.registrationCompletionTimer);
      this.registrationCompletionTimer = null;
    }
    this.registrationCompleted.set(false);
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
