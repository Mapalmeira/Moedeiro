import { HttpErrorResponse } from '@angular/common/http';
import { DialogShellComponent } from '../../../shared/ui/dialog-shell.component';
import { ChangeDetectionStrategy, Component, inject, input, output, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../../core/api/api-error';
import { AuthService } from '../../../core/auth/auth.service';
import { I18nService } from '../../../core/i18n/i18n.service';
import {
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  TOTP_PATTERN,
  USER_NAME_MAX_LENGTH,
  USER_NAME_PATTERN,
} from '../../../shared/forms/backend-validators';
import { CrockfordCodeInputDirective, normalizeCrockfordCode } from '../../../shared/forms/crockford-code-input.directive';
import { NoWhitespaceInputDirective } from '../../../shared/forms/no-whitespace-input.directive';
import { FieldErrorComponent } from '../../../shared/ui/field-error.component';
import { FormMessageComponent } from '../../../shared/ui/form-message.component';
import { IconComponent } from '../../../shared/ui/icon.component';

@Component({
  selector: 'app-password-recovery-dialog',
  standalone: true,
  imports: [DialogShellComponent, ReactiveFormsModule, CrockfordCodeInputDirective, NoWhitespaceInputDirective, FieldErrorComponent, FormMessageComponent, IconComponent],
  template: `
    @if (open()) {
      <app-dialog-shell [ariaLabel]="i18n.t('auth.recovery.title')" dialogWidth="550px" (dismiss)="requestClose()">
        <header class="dialog__header ui-dialog-header">
          <div class="dialog__title ui-dialog-title">
            <span class="title-icon title-icon--green"><app-icon name="key" [size]="21" /></span>
            <h2>{{ i18n.t('auth.recovery.title') }}</h2>
          </div>
          <button class="icon-button icon-button--control ui-action-press" type="button" (click)="requestClose()" [attr.aria-label]="i18n.t('common.close')">
            <app-icon name="x" [size]="19" />
          </button>
        </header>

        <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
          <label class="field" [class.ui-field-feedback--rejected]="recoveryCredentialsRejected()">
            <span>{{ i18n.t('auth.username') }} <span class="required-mark" aria-hidden="true">*</span></span>
            <input appNoWhitespace formControlName="name" autocomplete="username" (input)="clearRecoveryCredentialsRejection()" (animationend)="clearRecoveryCredentialsRejection()" [attr.aria-invalid]="recoveryCredentialsRejected()" [attr.aria-describedby]="recoveryCredentialsRejected() ? 'recovery-credentials-feedback' : null" />
            <app-field-error [text]="usernameError(form.controls.name)" />
          </label>

          <label class="field" [class.ui-field-feedback--rejected]="recoveryCredentialsRejected()">
            <span>{{ i18n.t('auth.recovery.code') }} <span class="required-mark" aria-hidden="true">*</span></span>
            <input appCrockfordCode formControlName="recovery_code" autocomplete="off" (input)="clearRecoveryCredentialsRejection()" (animationend)="clearRecoveryCredentialsRejection()" [attr.aria-invalid]="recoveryCredentialsRejected()" [attr.aria-describedby]="recoveryCredentialsRejected() ? 'recovery-credentials-feedback' : null" />
            <app-field-error [text]="codeError(form.controls.recovery_code)" />
            <app-field-error messageId="recovery-credentials-feedback" [visuallyHidden]="true" [text]="recoveryCredentialsFeedback()" />
          </label>

          <label class="field">
            <span>{{ i18n.t('auth.recovery.newPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
            <div class="input-with-action">
              <input appNoWhitespace [type]="showPassword() ? 'text' : 'password'" formControlName="new_password" autocomplete="new-password" />
              <button type="button" class="icon-action" (click)="showPassword.set(!showPassword())"
                [attr.aria-label]="showPassword() ? i18n.t('auth.password.hide') : i18n.t('auth.password.show')">
                <app-icon [name]="showPassword() ? 'eye-off' : 'eye'" />
              </button>
            </div>
            <app-field-error [text]="passwordError(form.controls.new_password)" />
          </label>

          <label class="field">
            <span>{{ i18n.t('auth.recovery.confirmPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
            <input appNoWhitespace type="password" formControlName="confirm_password" autocomplete="new-password" />
            <app-field-error [text]="confirmPasswordError()" />
          </label>

          @if (totpRequired()) {
            <label class="field" [class.ui-field-feedback--rejected]="totpRequiredRejected()">
              <span>{{ i18n.t('auth.totp') }} <span class="required-mark" aria-hidden="true">*</span></span>
              <input inputmode="numeric" autocomplete="one-time-code" formControlName="totp_code" maxlength="6" (input)="clearTotpRequiredRejection()" (animationend)="clearTotpRequiredRejection()" [attr.aria-invalid]="totpRequiredRejected()" [attr.aria-describedby]="totpRequiredRejected() ? 'recovery-totp-required-feedback' : null" />
              <app-field-error [text]="totpError(form.controls.totp_code)" />
              <app-field-error messageId="recovery-totp-required-feedback" [visuallyHidden]="true" [text]="totpRequiredFeedback()" />
            </label>
          }

          @if (errorMessage()) { <app-form-message [text]="errorMessage()!" /> }
          @if (successMessage()) { <app-form-message kind="success" [text]="successMessage()!" /> }

          <footer class="ui-surface-actions">
            <button class="ui-button ui-button--green ui-button--full" type="submit"
              [disabled]="form.invalid || passwordMismatch() || loading() || completed()">
              <span>{{ i18n.t('auth.recovery.submit') }}</span>
              <app-icon name="arrow-right" />
            </button>
          </footer>
        </form>
      </app-dialog-shell>
    }
  `,
  styles: `
    form { display: grid; gap: var(--form-gap); padding: var(--space-5); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PasswordRecoveryDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly apiErrors = inject(ApiErrorService);
  readonly i18n = inject(I18nService);

  readonly open = input(false);
  readonly close = output<void>();
  readonly loading = signal(false);
  readonly completed = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly totpRequired = signal(false);
  readonly totpRequiredRejected = signal(false);
  readonly recoveryCredentialsRejected = signal(false);
  readonly showPassword = signal(false);

  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(USER_NAME_MAX_LENGTH), Validators.pattern(USER_NAME_PATTERN)]],
    recovery_code: ['', Validators.required],
    new_password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH), Validators.maxLength(PASSWORD_MAX_LENGTH)]],
    confirm_password: ['', [Validators.required, Validators.maxLength(PASSWORD_MAX_LENGTH)]],
    totp_code: [''],
  });

  ngOnChanges(): void {
    if (this.open()) this.reset();
  }

  requestClose(): void {
    if (this.loading()) return;
    this.close.emit();
  }

  passwordMismatch(): boolean {
    const value = this.form.getRawValue();
    return !!value.confirm_password && value.new_password !== value.confirm_password;
  }

  submit(): void {
    if (this.form.invalid || this.passwordMismatch() || this.loading() || this.completed()) {
      this.form.markAllAsTouched();
      return;
    }

    this.loading.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.clearRecoveryCredentialsRejection();
    const value = this.form.getRawValue();
    this.auth.recoverPassword({
      name: value.name,
      recovery_code: normalizeCrockfordCode(value.recovery_code),
      new_password: value.new_password,
      totp_code: value.totp_code.trim() || null,
    }).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: () => {
        this.successMessage.set(this.i18n.t('auth.recovery.success'));
        this.completed.set(true);
        this.form.disable();
      },
      error: (error: unknown) => {
        if (error instanceof HttpErrorResponse && error.status === 401 && error.error?.detail === 'TOTP required') {
          this.totpRequired.set(true);
          this.totpRequiredRejected.set(true);
          this.form.controls.totp_code.setValidators([Validators.required, Validators.pattern(TOTP_PATTERN)]);
          this.form.controls.totp_code.updateValueAndValidity();
        } else if (error instanceof HttpErrorResponse && error.error?.detail === 'Invalid credentials') this.recoveryCredentialsRejected.set(true);
        else this.errorMessage.set(this.apiErrors.message(error, 'errors.recoveryFailed'));
      },
    });
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

  clearTotpRequiredRejection(): void {
    this.totpRequiredRejected.set(false);
  }

  totpRequiredFeedback(): string | null {
    return this.totpRequiredRejected() ? this.i18n.t('errors.totpRequired') : null;
  }

  clearRecoveryCredentialsRejection(): void {
    this.recoveryCredentialsRejected.set(false);
  }

  recoveryCredentialsFeedback(): string | null {
    return this.recoveryCredentialsRejected() ? this.i18n.t('errors.recoveryFailed') : null;
  }

  confirmPasswordError(): string | null {
    const control = this.form.controls.confirm_password;
    if (!this.shouldShowError(control)) return null;
        if (control.hasError('maxlength')) return this.i18n.t('validation.password.max', { max: PASSWORD_MAX_LENGTH });
    if (this.passwordMismatch()) return this.i18n.t('auth.register.passwordMismatch');
    return null;
  }

  private shouldShowError(control: AbstractControl): boolean {
    return control.invalid && control.dirty;
  }

  private reset(): void {
    this.form.enable();
    this.form.reset({ name: '', recovery_code: '', new_password: '', confirm_password: '', totp_code: '' });
    this.form.controls.totp_code.clearValidators();
    this.form.controls.totp_code.updateValueAndValidity({ emitEvent: false });
    this.loading.set(false);
    this.completed.set(false);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.totpRequired.set(false);
    this.totpRequiredRejected.set(false);
    this.recoveryCredentialsRejected.set(false);
    this.showPassword.set(false);
  }
}
