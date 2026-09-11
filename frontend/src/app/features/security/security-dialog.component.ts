import { HttpErrorResponse } from '@angular/common/http';
import { DialogShellComponent } from '../../shared/ui/dialog-shell.component';
import { ChangeDetectionStrategy, Component, HostListener, effect, inject, input, output, signal, untracked } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { toDataURL } from 'qrcode';
import { ApiErrorService } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';
import { I18nService } from '../../core/i18n/i18n.service';
import { SecurityService } from '../../core/security/security.service';
import {
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  TOTP_PATTERN,
} from '../../shared/forms/backend-validators';
import { NoWhitespaceInputDirective } from '../../shared/forms/no-whitespace-input.directive';
import { FieldErrorComponent } from '../../shared/ui/field-error.component';
import { FormMessageComponent } from '../../shared/ui/form-message.component';
import { IconComponent } from '../../shared/ui/icon.component';

@Component({
  selector: 'app-security-dialog',
  standalone: true,
  imports: [DialogShellComponent, ReactiveFormsModule, NoWhitespaceInputDirective, FieldErrorComponent, FormMessageComponent, IconComponent],
  template: `
    @if (open()) {
      <app-dialog-shell [ariaLabel]="i18n.t('security.title')" (dismiss)="requestClose()">

        <div class="dialog security-dialog">
        <header class="dialog__header ui-dialog-header">
          <div class="dialog__title ui-dialog-title">
            <span class="title-icon title-icon--blue"><app-icon name="shield" [size]="21" /></span>
            <h2>{{ i18n.t('security.title') }}</h2>
          </div>
          <button class="icon-button icon-button--control ui-action-press" type="button" (click)="requestClose()" [disabled]="busy()"
            [attr.aria-label]="i18n.t('common.close')">
            <app-icon name="x" [size]="19" />
          </button>
        </header>

        <div class="dialog__body">
          <section class="security-section">
            <h3>{{ i18n.t('security.password.title') }}</h3>

            <app-form-message kind="info" [text]="i18n.t('security.password.logoutWarning')" />

            <form class="security-form" [formGroup]="passwordForm" (ngSubmit)="changePassword()" novalidate>
                <div class="password-grid" [class.password-grid--totp]="totpStatus() === 'ENABLED'">
                <label class="field password-grid__current" [class.ui-field-feedback--rejected]="passwordCurrentRejected()">
                  <span>{{ i18n.t('security.currentPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
                  <input appNoWhitespace type="password" autocomplete="current-password" formControlName="current_password" required (input)="clearCredentialRejections()" (animationend)="clearCredentialRejections()" [attr.aria-invalid]="passwordCurrentRejected()" [attr.aria-describedby]="passwordCurrentRejected() ? 'password-current-feedback' : null" />
                  <app-field-error [text]="passwordError(passwordForm.controls.current_password)" />
                  <app-field-error messageId="password-current-feedback" [visuallyHidden]="true" [text]="passwordCurrentFeedback()" />
                </label>

                @if (totpStatus() === 'ENABLED') {
                  <label class="field" [class.ui-field-feedback--rejected]="totpCodeRejection() === 'password'">
                    <span>{{ i18n.t('auth.totp') }} <span class="required-mark" aria-hidden="true">*</span></span>
                    <input inputmode="numeric" autocomplete="one-time-code" formControlName="totp_code" maxlength="6" required (input)="clearTotpCodeRejection()" (animationend)="clearTotpCodeRejection()" [attr.aria-invalid]="totpCodeRejection() === 'password'" [attr.aria-describedby]="totpCodeRejection() === 'password' ? 'password-totp-feedback' : null" />
                    <app-field-error [text]="totpError(passwordForm.controls.totp_code)" />
                    <app-field-error messageId="password-totp-feedback" [visuallyHidden]="true" [text]="passwordTotpFeedback()" />
                  </label>
                }

                <label class="field">
                  <span>{{ i18n.t('security.newPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
                  <input appNoWhitespace type="password" autocomplete="new-password" formControlName="new_password" required />
                  <app-field-error [text]="passwordError(passwordForm.controls.new_password)" />
                </label>

                <label class="field">
                  <span>{{ i18n.t('security.confirmPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
                  <input appNoWhitespace type="password" autocomplete="new-password" formControlName="confirm_password" required />
                  <app-field-error [text]="confirmPasswordError()" />
                </label>
              </div>

              @if (passwordErrorMessage()) { <app-form-message [text]="passwordErrorMessage()!" /> }

              <div class="section-actions password-actions ui-surface-actions">
                <button class="ui-button ui-button--blue security-action-button" type="submit"
                  [disabled]="passwordForm.invalid || passwordMismatch() || changingPassword() || loadingTotpStatus() || totpStatus() === 'unknown'">
                  {{ i18n.t('security.password.change') }}
                </button>
              </div>
            </form>
          </section>

          <section class="security-section security-section--totp">
            <h3>{{ i18n.t('security.totp.title') }}</h3>

            @if (totpInfoMessage()) { <app-form-message kind="info" [text]="totpInfoMessage()!" /> }
            @if (totpExpiryErrorMessage()) { <app-form-message [text]="totpExpiryErrorMessage()!" /> }
            @if (totpSuccessMessage()) { <app-form-message kind="info" [text]="totpSuccessMessage()!" /> }

            @if (loadingTotpStatus()) {
              <div class="totp-status-state ui-projected-surface" role="status" aria-live="polite">
                <span class="totp-status-spinner ui-spinner" aria-hidden="true"></span>
                <span>{{ i18n.t('security.totp.checking') }}</span>
              </div>
            } @else if (totpStatus() === 'unknown') {
              <div class="totp-status-state totp-status-state--error ui-projected-surface">
                @if (totpStatusErrorMessage()) { <app-form-message [text]="totpStatusErrorMessage()!" /> }
              </div>
            } @else if (totpStatus() === 'ENABLED') {
              <form class="security-form totp-form" [formGroup]="disableTotpForm" (ngSubmit)="disableTotp()" novalidate>
                <div class="form-grid">
                  <label class="field" [class.ui-field-feedback--rejected]="disablePasswordRejected() || disableCredentialsRejected()">
                    <span>{{ i18n.t('security.currentPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
                    <input appNoWhitespace type="password" autocomplete="current-password" formControlName="current_password" required (input)="clearCredentialRejections()" (animationend)="clearCredentialRejections()" [attr.aria-invalid]="disablePasswordRejected() || disableCredentialsRejected()" [attr.aria-describedby]="disableCredentialsRejected() ? 'disable-credentials-feedback' : disablePasswordRejected() ? 'disable-password-feedback' : null" />
                    <app-field-error [text]="passwordError(disableTotpForm.controls.current_password)" />
                    <app-field-error messageId="disable-password-feedback" [visuallyHidden]="true" [text]="disablePasswordFeedback()" />
                  </label>

                  <label class="field" [class.ui-field-feedback--rejected]="disableTotpCodeRejected() || disableCredentialsRejected()">
                    <span>{{ i18n.t('auth.totp') }} <span class="required-mark" aria-hidden="true">*</span></span>
                    <input inputmode="numeric" autocomplete="one-time-code" formControlName="code" maxlength="6" required (input)="clearCredentialRejections()" (animationend)="clearCredentialRejections()" [attr.aria-invalid]="disableTotpCodeRejected() || disableCredentialsRejected()" [attr.aria-describedby]="disableCredentialsRejected() ? 'disable-credentials-feedback' : disableTotpCodeRejected() ? 'disable-totp-feedback' : null" />
                    <app-field-error [text]="totpError(disableTotpForm.controls.code)" />
                    <app-field-error messageId="disable-totp-feedback" [visuallyHidden]="true" [text]="disableTotpCodeFeedback()" />
                  </label>
                </div>

                <app-field-error messageId="disable-credentials-feedback" [visuallyHidden]="true" [text]="disableCredentialsFeedback()" />

                @if (totpErrorMessage()) { <app-form-message [text]="totpErrorMessage()!" /> }

                <div class="section-actions ui-surface-actions">
                  <button class="ui-button ui-button--danger security-action-button" type="submit" [disabled]="disableTotpForm.invalid || disablingTotp()">
                    {{ i18n.t('security.totp.disable') }}
                  </button>
                </div>
              </form>
            } @else {
              @if (!provisioningUri()) {
                <form class="security-form totp-form" [formGroup]="setupForm" (ngSubmit)="startTotpSetup()" novalidate>
                  <div class="setup-row">
                    <label class="field" [class.ui-field-feedback--rejected]="setupPasswordRejected()">
                      <span>{{ i18n.t('security.currentPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
                      <input appNoWhitespace type="password" autocomplete="current-password" formControlName="current_password" required (input)="clearCredentialRejections()" (animationend)="clearCredentialRejections()" [attr.aria-invalid]="setupPasswordRejected()" [attr.aria-describedby]="setupPasswordRejected() ? 'setup-password-feedback' : null" />
                      <app-field-error [text]="passwordError(setupForm.controls.current_password)" />
                      <app-field-error messageId="setup-password-feedback" [visuallyHidden]="true" [text]="setupPasswordFeedback()" />
                    </label>

                    <button class="ui-button ui-button--blue security-action-button" type="submit" [disabled]="setupForm.invalid || startingTotp()">
                      {{ i18n.t('security.totp.start') }}
                    </button>
                  </div>

                  @if (totpErrorMessage()) { <app-form-message [text]="totpErrorMessage()!" /> }
                </form>
              } @else {
                <div class="totp-setup">
                  <div class="qr-wrap ui-projected-surface ui-projection--surface">
                    @if (qrDataUrl()) {
                      <img [src]="qrDataUrl()!" [alt]="i18n.t('security.totp.qrAlt')" width="220" height="220" />
                    } @else {
                      <div class="qr-loading">…</div>
                    }
                  </div>

                  <form class="confirm-form totp-setup__side" [formGroup]="confirmTotpForm" (ngSubmit)="confirmTotp()" novalidate>
                    <div class="totp-setup__fields">
                      <div class="secret-block">
                        <span class="secret-block__label">{{ i18n.t('security.totp.secret') }}</span>
                        <div class="secret-value ui-projected-surface">
                          <code>{{ secretVisible() ? totpSecret() : maskedTotpSecret() }}</code>
                          <button class="secret-visibility-button" type="button" (click)="toggleSecretVisibility()"
                            [attr.aria-label]="secretVisible() ? i18n.t('security.totp.hideSecret') : i18n.t('security.totp.showSecret')">
                            <app-icon [name]="secretVisible() ? 'eye-off' : 'eye'" [size]="17" />
                          </button>
                          <button class="copy-button" type="button" (click)="copySecret()"
                            [attr.aria-label]="secretCopied() ? i18n.t('security.totp.copied') : i18n.t('security.totp.copySecret')">
                            <app-icon [name]="secretCopied() ? 'check' : 'copy'" [size]="17" />
                          </button>
                        </div>
                      </div>

                      <div class="totp-code-stack">
                        <label class="field totp-code-field" [class.ui-field-feedback--rejected]="totpCodeRejection() === 'confirm'">
                          <span>{{ i18n.t('auth.totp') }} <span class="required-mark" aria-hidden="true">*</span></span>
                          <input inputmode="numeric" autocomplete="one-time-code" formControlName="code" maxlength="6" required (input)="clearTotpCodeRejection()" (animationend)="clearTotpCodeRejection()" [attr.aria-invalid]="totpCodeRejection() === 'confirm'" [attr.aria-describedby]="totpCodeRejection() === 'confirm' ? 'confirm-totp-feedback' : null" />
                          <app-field-error [text]="totpError(confirmTotpForm.controls.code)" />
                          <app-field-error messageId="confirm-totp-feedback" [visuallyHidden]="true" [text]="confirmTotpFeedback()" />
                        </label>
                        @if (totpErrorMessage()) {
                          <app-form-message class="totp-code-message" [text]="totpErrorMessage()!" />
                        }
                      </div>
                    </div>

                    <div class="section-actions totp-setup__action ui-surface-actions">
                      <button class="ui-button ui-button--blue security-action-button" type="submit" [disabled]="confirmTotpForm.invalid || confirmingTotp()">
                        <span>{{ i18n.t('security.totp.confirm') }}</span>
                        @if (totpSetupRemainingTime(); as remainingTime) {
                          <span class="totp-setup__countdown" role="status" aria-live="polite" [attr.aria-label]="totpSetupExpiryMessage()">{{ remainingTime }}</span>
                        }
                      </button>
                    </div>
                  </form>
                </div>
              }
            }
          </section>
        </div>
      </div>
      </app-dialog-shell>
    }
  `,
  styles: `
    .security-dialog {
      --ui-accent: var(--blue);
      --ui-accent-strong: var(--blue-strong);
    }
    .dialog__header { position: sticky; top: 0; z-index: 2; background: var(--surface); }
    .dialog__body { padding: 0 var(--space-5) var(--space-5); }
    .security-section { display: grid; gap: var(--form-gap); padding: var(--section-gap) 0; border-bottom: var(--border-width) solid var(--line); }
    .security-section:last-child { border-bottom: 0; padding-bottom: 0; }
    .security-section h3 { margin: 0; font-size: 1rem; letter-spacing: -.005em; }
    .security-form, .confirm-form { display: grid; gap: var(--form-gap); }
    .password-grid, .form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--form-gap); }
    .password-grid__current { grid-column: 1 / -1; }
    .password-grid--totp .password-grid__current { grid-column: auto; }
    .section-actions { width: 100%; }
    .security-action-button { width: var(--action-button-min-width); min-width: var(--action-button-min-width); }
    .password-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--form-gap); justify-items: end; }
    .password-actions .security-action-button { grid-column: 2; }
    .totp-form { margin-top: var(--form-gap); }
    .totp-status-state { min-height: 78px; display: flex; align-items: center; justify-content: center; gap: var(--space-3); padding: var(--form-gap); border: var(--border-width) solid color-mix(in srgb, var(--blue-strong) 56%, var(--line)); border-radius: var(--radius-card); background: var(--surface); color: var(--text-muted); font-size: .86rem; font-weight: 700; box-shadow: var(--selection-shadow); }
    .totp-status-state--error { display: grid; justify-items: end; }
    .totp-status-spinner { --spinner-size: 20px; --ui-accent: var(--blue); --ui-accent-strong: var(--blue); }
    .setup-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; grid-template-rows: auto auto auto; column-gap: var(--form-gap); row-gap: var(--field-gap); align-items: stretch; }
    .setup-row .field { display: contents; }
    .setup-row .field > span { grid-column: 1; grid-row: 1; }
    .setup-row .field > input { grid-column: 1; grid-row: 2; }
    .setup-row .field > app-field-error { grid-column: 1; grid-row: 3; }
    .setup-row .security-action-button { grid-column: 2; grid-row: 2; height: var(--control-height); min-height: var(--control-height); }
    .totp-setup { display: grid; grid-template-columns: minmax(238px, .82fr) minmax(300px, 1.18fr); gap: var(--section-gap); margin-top: var(--section-gap); align-items: stretch; }
    .totp-setup__side { position: relative; min-width: 0; min-height: 100%; display: grid; grid-template-rows: minmax(0, 1fr) auto; gap: var(--form-gap); }
    .totp-setup__fields {
      grid-row: 1;
      display: grid;
      width: min(100%, 420px);
      gap: var(--section-gap);
      min-width: 0;
      justify-self: center;
      align-self: center;
    }
    .totp-setup__action { grid-row: 2; align-self: end; }
    .qr-wrap { box-sizing: border-box; display: grid; place-items: center; min-height: 280px; height: 100%; padding: var(--form-gap); border: var(--border-width) solid var(--blue-strong); border-radius: var(--radius-card); background: var(--surface); }
    .qr-wrap img { display: block; width: 220px; height: 220px; max-width: 100%; image-rendering: pixelated; }
    .qr-loading { color: var(--text); font-size: 1.4rem; }
    .secret-block, .totp-code-field { display: grid; gap: var(--field-gap); min-width: 0; }
    .secret-block__label, .totp-code-field > span { display: block; font-size: .86rem; font-weight: 760; }
    .totp-code-stack { min-width: 0; display: grid; gap: var(--field-gap); }
    .totp-code-field > input { display: block; }
    .totp-code-field > app-field-error { display: block; }
    .totp-code-message { display: block; min-width: 0; }
    .totp-setup__countdown { padding-inline-start: var(--space-2); border-inline-start: var(--border-width) solid color-mix(in srgb, var(--on-blue) 42%, transparent); color: var(--on-blue); font: inherit; font-variant-numeric: tabular-nums; line-height: 1; }
    .secret-value { display: grid; grid-template-columns: minmax(0, 1fr) var(--menu-item-height) var(--menu-item-height); align-items: stretch; min-height: var(--control-height); border: var(--border-width) solid var(--blue-strong); border-radius: var(--radius-sm); background: var(--surface); box-shadow: var(--selection-shadow); }
    .secret-value code { min-width: 0; display: flex; align-items: center; min-height: calc(var(--control-height) - (2 * var(--border-width))); padding: var(--space-2) var(--control-padding-inline); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: .82rem; color: var(--text); }
    .secret-visibility-button, .copy-button { box-sizing: border-box; display: grid; place-items: center; width: var(--menu-item-height); min-width: var(--menu-item-height); height: 100%; min-height: calc(var(--control-height) - (2 * var(--border-width))); margin: 0; padding: 0; border: 0; border-left: var(--border-width) solid var(--blue-strong); border-radius: 0; font: inherit; line-height: 1; transition: background var(--motion-press) ease, color var(--motion-press) ease; }
    .secret-visibility-button { background: var(--surface); color: var(--text); }
    .copy-button { background: var(--blue); color: var(--on-blue); }
    .secret-visibility-button:hover { background: var(--surface-muted); }
    .copy-button:hover { background: color-mix(in srgb, var(--blue) 88%, white); }
    .secret-visibility-button:active { background: color-mix(in srgb, var(--surface-muted) 78%, var(--blue-soft)); }
    .copy-button:active { background: color-mix(in srgb, var(--blue) 80%, var(--blue-strong)); }
    .confirm-form { padding: 0; border: 0; background: transparent; }
    .confirm-form .section-actions { justify-content: flex-end; }
    @media (max-width: 700px) {
      .totp-setup { grid-template-columns: 1fr; align-items: start; gap: var(--space-7); }
      .qr-wrap {
        width: min(280px, 100%);
        height: auto;
        min-height: 0;
        aspect-ratio: 1;
        justify-self: center;
      }
      .qr-wrap img { width: min(220px, 100%); height: auto; aspect-ratio: 1; }
      .totp-setup__side { min-height: 0; grid-template-rows: auto auto; }
      .totp-setup__fields { width: 100%; align-self: stretch; }
      .secret-value {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        grid-template-rows: minmax(46px, auto) 42px;
      }
      .secret-value code {
        grid-column: 1 / -1;
        grid-row: 1;
        width: 100%;
        min-height: var(--control-height);
        padding-inline: var(--control-padding-inline);
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
      }
      .secret-visibility-button, .copy-button {
        grid-row: 2;
        width: auto;
        min-width: 0;
        min-height: 42px;
        border-top: var(--border-width) solid var(--blue-strong);
      }
      .secret-visibility-button { grid-column: 1; border-left: 0; }
      .copy-button { grid-column: 2; border-left: var(--border-width) solid var(--blue-strong); }
    }
    @media (max-width: 620px) {
      .password-grid, .form-grid, .setup-row, .password-actions { grid-template-columns: 1fr; }
      .password-grid__current, .password-grid--totp .password-grid__current { grid-column: 1; }
      .password-actions .security-action-button { grid-column: 1; }
      .setup-row .field > span { grid-column: 1; grid-row: 1; }
      .setup-row .field > input { grid-column: 1; grid-row: 2; }
      .setup-row .field > app-field-error { grid-column: 1; grid-row: 3; }
      .setup-row .security-action-button { grid-column: 1; grid-row: 4; width: 100%; min-width: 0; margin-top: var(--space-1); }
      .section-actions .security-action-button { width: 100%; min-width: 0; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SecurityDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly security = inject(SecurityService);
  private readonly auth = inject(AuthService);
  private readonly apiErrors = inject(ApiErrorService);
  readonly i18n = inject(I18nService);

  readonly open = input(false);
  readonly close = output<void>();

  readonly changingPassword = signal(false);
  readonly startingTotp = signal(false);
  readonly confirmingTotp = signal(false);
  readonly disablingTotp = signal(false);
  readonly loadingTotpStatus = signal(false);
  readonly passwordErrorMessage = signal<string | null>(null);
  readonly totpErrorMessage = signal<string | null>(null);
  readonly totpStatusErrorMessage = signal<string | null>(null);
  readonly totpInfoMessage = signal<string | null>(null);
  readonly totpExpiryErrorMessage = signal<string | null>(null);
  readonly totpSuccessMessage = signal<string | null>(null);
  readonly totpCodeRejection = signal<'password' | 'confirm' | null>(null);
  readonly passwordCurrentRejected = signal(false);
  readonly setupPasswordRejected = signal(false);
  readonly disablePasswordRejected = signal(false);
  readonly disableTotpCodeRejected = signal(false);
  readonly disableCredentialsRejected = signal(false);
  readonly totpStatus = this.security.totpStatus;
  readonly provisioningUri = signal<string | null>(null);
  readonly totpSecret = signal('');
  readonly qrDataUrl = signal<string | null>(null);
  readonly setupExpiresAt = signal<number | null>(null);
  readonly setupSecondsRemaining = signal<number | null>(null);
  readonly secretCopied = signal(false);
  readonly secretVisible = signal(false);
  private setupExpiryTimer: ReturnType<typeof setInterval> | null = null;

  readonly passwordForm = this.fb.nonNullable.group({
    current_password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH), Validators.maxLength(PASSWORD_MAX_LENGTH)]],
    new_password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH), Validators.maxLength(PASSWORD_MAX_LENGTH)]],
    confirm_password: ['', [Validators.required, Validators.maxLength(PASSWORD_MAX_LENGTH)]],
    totp_code: [''],
  });

  readonly setupForm = this.fb.nonNullable.group({
    current_password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH), Validators.maxLength(PASSWORD_MAX_LENGTH)]],
  });

  readonly confirmTotpForm = this.fb.nonNullable.group({
    code: ['', [Validators.required, Validators.pattern(TOTP_PATTERN)]],
  });

  readonly disableTotpForm = this.fb.nonNullable.group({
    current_password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH), Validators.maxLength(PASSWORD_MAX_LENGTH)]],
    code: ['', [Validators.required, Validators.pattern(TOTP_PATTERN)]],
  });

  constructor() {
    effect(() => {
      if (this.open()) {
        untracked(() => {
          this.resetDialog();
          this.loadTotpStatus();
        });
      }
    });

    effect(() => {
      const control = this.passwordForm.controls.totp_code;

      if (this.totpStatus() === 'ENABLED') {
        control.setValidators([Validators.required, Validators.pattern(TOTP_PATTERN)]);
      } else {
        control.clearValidators();
        control.setValue('', { emitEvent: false });
      }

      control.updateValueAndValidity({ emitEvent: false });
    });
  }

  busy(): boolean {
    return this.changingPassword() || this.startingTotp() || this.confirmingTotp() || this.disablingTotp();
  }

  @HostListener('document:visibilitychange')
  onVisibilityChange(): void {
    if (this.open() && document.visibilityState === 'visible') this.updateSetupExpiry();
  }

  requestClose(): void {
    if (this.busy()) return;
    this.resetDialog();
    this.close.emit();
  }

  loadTotpStatus(): void {
    if (this.loadingTotpStatus()) return;

    this.loadingTotpStatus.set(true);
    this.totpStatusErrorMessage.set(null);
    this.resetTotpFormsAndProvisioning();

    this.security.getTotpStatus().pipe(
      finalize(() => this.loadingTotpStatus.set(false)),
    ).subscribe({
      next: ({ state, provisioning_uri, expires_at }) => {
        if (state === 'PENDING' && provisioning_uri !== null && expires_at !== null) {
          this.applyPendingTotpSetup(provisioning_uri, expires_at);
        }
      },
      error: (error: unknown) => {
        this.totpStatusErrorMessage.set(this.apiErrors.message(error, 'errors.totpStatusFailed'));
      },
    });
  }

  changePassword(): void {
    if (this.passwordForm.invalid || this.passwordMismatch() || this.changingPassword()) return;
    this.changingPassword.set(true);
    this.passwordErrorMessage.set(null);
    this.clearCredentialRejections();
    const value = this.passwordForm.getRawValue();

    this.security.changePassword({
      current_password: value.current_password,
      new_password: value.new_password,
      totp_code: value.totp_code.trim() || null,
    }).pipe(finalize(() => this.changingPassword.set(false))).subscribe({
      next: () => void this.auth.finishLogout({ passwordChanged: true }),
      error: (error: unknown) => {
        if (this.isInvalidTotpCode(error)) this.rejectTotpCode('password');
        else if (this.hasErrorDetail(error, 'Invalid current password')) this.passwordCurrentRejected.set(true);
        else this.passwordErrorMessage.set(this.apiErrors.message(error, 'errors.passwordChangeFailed'));
      },
    });
  }

  startTotpSetup(): void {
    if (this.setupForm.invalid || this.startingTotp()) return;
    this.startingTotp.set(true);
    this.clearTotpMessages();
    this.clearCredentialRejections();

    this.security.startTotpSetup(this.setupForm.getRawValue()).pipe(finalize(() => this.startingTotp.set(false))).subscribe({
      next: (response) => {
        if (response.state !== 'PENDING' || response.provisioning_uri === null || response.expires_at === null) {
          this.totpErrorMessage.set(this.i18n.t('errors.totpSetupFailed'));
          return;
        }
        this.setupForm.reset({ current_password: '' });
        this.applyPendingTotpSetup(response.provisioning_uri, response.expires_at);
      },
      error: (error: unknown) => {
        if (this.hasErrorDetail(error, 'Invalid current password')) this.setupPasswordRejected.set(true);
        else this.totpErrorMessage.set(this.apiErrors.message(error, 'errors.totpSetupFailed'));
      },
    });
  }

  confirmTotp(): void {
    if (this.confirmTotpForm.invalid || this.confirmingTotp()) return;
    this.confirmingTotp.set(true);
    this.clearTotpMessages();

    this.security.confirmTotp(this.confirmTotpForm.getRawValue()).pipe(finalize(() => this.confirmingTotp.set(false))).subscribe({
      next: () => {
        this.resetTotpFormsAndProvisioning();
        this.totpInfoMessage.set(this.i18n.t('security.totp.enabled'));
      },
      error: (error: unknown) => {
        if (this.isInvalidTotpCode(error)) this.rejectTotpCode('confirm');
        else this.totpErrorMessage.set(this.apiErrors.message(error, 'errors.totpConfirmFailed'));
      },
    });
  }

  disableTotp(): void {
    if (this.totpStatus() !== 'ENABLED' || this.disableTotpForm.invalid || this.disablingTotp()) return;
    this.disablingTotp.set(true);
    this.clearTotpMessages();
    this.clearCredentialRejections();

    this.security.disableTotp(this.disableTotpForm.getRawValue()).pipe(finalize(() => this.disablingTotp.set(false))).subscribe({
      next: () => {
        this.resetTotpFormsAndProvisioning();
        this.totpSuccessMessage.set(this.i18n.t('security.totp.disabled'));
      },
      error: (error: unknown) => {
        if (this.hasErrorDetail(error, 'Invalid current password')) this.disablePasswordRejected.set(true);
        else if (this.isInvalidTotpCode(error)) this.disableTotpCodeRejected.set(true);
        else if (this.hasErrorDetail(error, 'Invalid credentials')) this.disableCredentialsRejected.set(true);
        else this.totpErrorMessage.set(this.apiErrors.message(error, 'errors.totpDisableFailed'));
      },
    });
  }

  passwordMismatch(): boolean {
    const value = this.passwordForm.getRawValue();
    return !!value.confirm_password && value.new_password !== value.confirm_password;
  }

  passwordError(control: AbstractControl): string | null {
    if (!this.shouldShowError(control)) return null;
    if (control.hasError('minlength')) return this.i18n.t('validation.password.min', { min: PASSWORD_MIN_LENGTH });
    if (control.hasError('maxlength')) return this.i18n.t('validation.password.max', { max: PASSWORD_MAX_LENGTH });
    return null;
  }

  confirmPasswordError(): string | null {
    const control = this.passwordForm.controls.confirm_password;
    if (!this.shouldShowError(control)) return null;
    if (control.hasError('maxlength')) return this.i18n.t('validation.password.max', { max: PASSWORD_MAX_LENGTH });
    if (this.passwordMismatch()) return this.i18n.t('auth.register.passwordMismatch');
    return null;
  }

  totpError(control: AbstractControl): string | null {
    if (!this.shouldShowError(control)) return null;
    return control.hasError('pattern') ? this.i18n.t('validation.totp.invalid') : null;
  }

  totpSetupRemainingTime(): string | null {
    const remaining = this.setupSecondsRemaining();
    if (remaining === null) return null;
    const minutes = Math.floor(remaining / 60);
    const seconds = remaining % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }

  totpSetupExpiryMessage(): string | null {
    const time = this.totpSetupRemainingTime();
    return time === null ? null : this.i18n.t('security.totp.expiresIn', { time });
  }

  clearTotpCodeRejection(): void {
    this.totpCodeRejection.set(null);
  }

  clearCredentialRejections(): void {
    this.passwordCurrentRejected.set(false);
    this.setupPasswordRejected.set(false);
    this.disablePasswordRejected.set(false);
    this.disableTotpCodeRejected.set(false);
    this.disableCredentialsRejected.set(false);
  }

  passwordCurrentFeedback(): string | null {
    return this.passwordCurrentRejected() ? this.i18n.t('errors.invalidCurrentPassword') : null;
  }

  passwordTotpFeedback(): string | null {
    return this.totpCodeRejection() === 'password' ? this.i18n.t('feedback.invalidTotpCode') : null;
  }

  setupPasswordFeedback(): string | null {
    return this.setupPasswordRejected() ? this.i18n.t('errors.invalidCurrentPassword') : null;
  }

  confirmTotpFeedback(): string | null {
    return this.totpCodeRejection() === 'confirm' ? this.i18n.t('feedback.invalidTotpCode') : null;
  }

  disablePasswordFeedback(): string | null {
    return this.disablePasswordRejected() ? this.i18n.t('errors.invalidCurrentPassword') : null;
  }

  disableTotpCodeFeedback(): string | null {
    return this.disableTotpCodeRejected() ? this.i18n.t('feedback.invalidTotpCode') : null;
  }

  disableCredentialsFeedback(): string | null {
    return this.disableCredentialsRejected() ? this.i18n.t('errors.totpDisableFailed') : null;
  }


  toggleSecretVisibility(): void {
    this.secretVisible.update((visible) => !visible);
  }

  maskedTotpSecret(): string {
    return '•'.repeat(this.totpSecret().length);
  }

  async copySecret(): Promise<void> {
    const secret = this.totpSecret();
    if (!secret) return;

    try {
      await navigator.clipboard.writeText(secret);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = secret;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      textarea.remove();
    }

    this.secretCopied.set(true);
    setTimeout(() => this.secretCopied.set(false), 1800);
  }

  private async renderQrCode(provisioningUri: string): Promise<void> {
    try {
      const qrDataUrl = await toDataURL(provisioningUri, { width: 220, margin: 2, errorCorrectionLevel: 'M' });
      if (this.provisioningUri() === provisioningUri) this.qrDataUrl.set(qrDataUrl);
    } catch {
      // The secret remains copyable even if local QR rendering fails.
      if (this.provisioningUri() === provisioningUri) this.qrDataUrl.set(null);
    }
  }

  private extractSecret(provisioningUri: string): string {
    return new URL(provisioningUri).searchParams.get('secret') ?? '';
  }

  private shouldShowError(control: AbstractControl): boolean {
    return control.invalid && control.dirty;
  }

  private clearTotpMessages(): void {
    this.totpErrorMessage.set(null);
    this.totpInfoMessage.set(null);
    this.totpExpiryErrorMessage.set(null);
    this.totpSuccessMessage.set(null);
  }

  private resetTotpFormsAndProvisioning(): void {
    this.stopSetupExpiryCountdown();
    this.setupForm.reset({ current_password: '' });
    this.confirmTotpForm.reset({ code: '' });
    this.disableTotpForm.reset({ current_password: '', code: '' });
    this.provisioningUri.set(null);
    this.totpSecret.set('');
    this.qrDataUrl.set(null);
    this.setupExpiresAt.set(null);
    this.setupSecondsRemaining.set(null);
    this.secretCopied.set(false);
    this.secretVisible.set(false);
    this.clearTotpCodeRejection();
    this.clearCredentialRejections();
  }

  private resetDialog(): void {
    this.passwordForm.reset({ current_password: '', new_password: '', confirm_password: '', totp_code: '' });
    this.passwordErrorMessage.set(null);
    this.totpStatusErrorMessage.set(null);
    this.resetTotpFormsAndProvisioning();
    this.clearTotpMessages();
  }

  private startSetupExpiryCountdown(setupExpiresAt: number): void {
    this.stopSetupExpiryCountdown();
    this.setupExpiresAt.set(setupExpiresAt);
    this.updateSetupExpiry();
    if (this.setupExpiresAt() !== null) {
      this.setupExpiryTimer = setInterval(() => this.updateSetupExpiry(), 1_000);
    }
  }

  private updateSetupExpiry(): void {
    const setupExpiresAt = this.setupExpiresAt();
    if (setupExpiresAt === null) return;

    const remaining = Math.max(0, setupExpiresAt - Math.floor(Date.now() / 1_000));
    if (remaining > 0) {
      this.setupSecondsRemaining.set(remaining);
      return;
    }

    this.resetTotpFormsAndProvisioning();
    this.totpExpiryErrorMessage.set(this.i18n.t('security.totp.expired'));
  }

  private stopSetupExpiryCountdown(): void {
    if (this.setupExpiryTimer !== null) {
      clearInterval(this.setupExpiryTimer);
      this.setupExpiryTimer = null;
    }
  }

  private rejectTotpCode(field: 'password' | 'confirm'): void {
    this.totpCodeRejection.set(field);
  }

  private isInvalidTotpCode(error: unknown): boolean {
    return error instanceof HttpErrorResponse && error.error?.detail === 'Invalid TOTP code';
  }

  private hasErrorDetail(error: unknown, detail: string): boolean {
    return error instanceof HttpErrorResponse && error.error?.detail === detail;
  }

  private applyPendingTotpSetup(provisioningUri: string, expiresAt: number): void {
    this.provisioningUri.set(provisioningUri);
    this.totpSecret.set(this.extractSecret(provisioningUri));
    this.startSetupExpiryCountdown(expiresAt);
    void this.renderQrCode(provisioningUri);
  }
}
