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
  imports: [ReactiveFormsModule, NoWhitespaceInputDirective, FieldErrorComponent, FormMessageComponent, IconComponent],
  template: `
    @if (open()) {
      <div class="dialog-backdrop" (click)="requestClose()" aria-hidden="true"></div>
      <section class="dialog security-dialog" role="dialog" aria-modal="true" [attr.aria-label]="i18n.t('security.title')">
        <header class="dialog__header">
          <div class="dialog__title">
            <span class="title-icon title-icon--blue"><app-icon name="shield" [size]="21" /></span>
            <h2>{{ i18n.t('security.title') }}</h2>
          </div>
          <button class="icon-button" type="button" (click)="requestClose()" [disabled]="busy()"
            [attr.aria-label]="i18n.t('common.close')">
            <app-icon name="x" [size]="19" />
          </button>
        </header>

        <div class="dialog__body">
          <section class="security-section">
            <h3>{{ i18n.t('security.password.title') }}</h3>

            <div class="notice-token">
              <app-icon name="info" [size]="18" />
              <span>{{ i18n.t('security.password.logoutWarning') }}</span>
            </div>

            <form class="security-form" [formGroup]="passwordForm" (ngSubmit)="changePassword()" novalidate>
              <div class="password-grid" [class.password-grid--totp]="totpStatus() === 'enabled'">
                <label class="field password-grid__current">
                  <span>{{ i18n.t('security.currentPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
                  <input appNoWhitespace type="password" autocomplete="current-password" formControlName="current_password" required />
                  <app-field-error [text]="passwordError(passwordForm.controls.current_password)" />
                </label>

                @if (totpStatus() === 'enabled') {
                  <label class="field">
                    <span>{{ i18n.t('auth.totp') }} <span class="required-mark" aria-hidden="true">*</span></span>
                    <input inputmode="numeric" autocomplete="one-time-code" formControlName="totp_code" maxlength="6" required />
                    <app-field-error [text]="totpError(passwordForm.controls.totp_code)" />
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

              <div class="section-actions password-actions">
                <button class="ui-button ui-button--blue security-action-button" type="submit"
                  [disabled]="passwordForm.invalid || passwordMismatch() || changingPassword() || loadingTotpStatus() || totpStatus() === 'unknown'">
                  {{ changingPassword() ? i18n.t('security.password.changing') : i18n.t('security.password.change') }}
                </button>
              </div>
            </form>
          </section>

          <section class="security-section security-section--totp">
            <h3>{{ i18n.t('security.totp.title') }}</h3>

            @if (totpInfoMessage()) { <app-form-message kind="info" [text]="totpInfoMessage()!" /> }
            @if (totpSuccessMessage()) { <app-form-message kind="success" [text]="totpSuccessMessage()!" /> }

            @if (loadingTotpStatus()) {
              <div class="totp-status-state" role="status" aria-live="polite">
                <span class="totp-status-spinner" aria-hidden="true"></span>
                <span>{{ i18n.t('security.totp.checking') }}</span>
              </div>
            } @else if (totpStatus() === 'unknown') {
              <div class="totp-status-state totp-status-state--error">
                @if (totpStatusErrorMessage()) { <app-form-message [text]="totpStatusErrorMessage()!" /> }
                <button class="ui-button ui-button--plain totp-status-retry" type="button" (click)="loadTotpStatus()">
                  {{ i18n.t('security.totp.retry') }}
                </button>
              </div>
            } @else if (totpStatus() === 'enabled') {
              <form class="security-form totp-form" [formGroup]="disableTotpForm" (ngSubmit)="disableTotp()" novalidate>
                <div class="form-grid">
                  <label class="field">
                    <span>{{ i18n.t('security.currentPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
                    <input appNoWhitespace type="password" autocomplete="current-password" formControlName="current_password" required />
                    <app-field-error [text]="passwordError(disableTotpForm.controls.current_password)" />
                  </label>

                  <label class="field">
                    <span>{{ i18n.t('auth.totp') }} <span class="required-mark" aria-hidden="true">*</span></span>
                    <input inputmode="numeric" autocomplete="one-time-code" formControlName="code" maxlength="6" required />
                    <app-field-error [text]="totpError(disableTotpForm.controls.code)" />
                  </label>
                </div>

                @if (totpErrorMessage()) { <app-form-message [text]="totpErrorMessage()!" /> }

                <div class="section-actions">
                  <button class="ui-button ui-button--danger security-action-button" type="submit" [disabled]="disableTotpForm.invalid || disablingTotp()">
                    {{ disablingTotp() ? i18n.t('security.totp.disabling') : i18n.t('security.totp.disable') }}
                  </button>
                </div>
              </form>
            } @else {
              @if (!provisioningUri()) {
                <form class="security-form totp-form" [formGroup]="setupForm" (ngSubmit)="startTotpSetup()" novalidate>
                  <div class="setup-row">
                    <label class="field">
                      <span>{{ i18n.t('security.currentPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
                      <input appNoWhitespace type="password" autocomplete="current-password" formControlName="current_password" required />
                      <app-field-error [text]="passwordError(setupForm.controls.current_password)" />
                    </label>

                    <button class="ui-button ui-button--blue security-action-button" type="submit" [disabled]="setupForm.invalid || startingTotp()">
                      {{ startingTotp() ? i18n.t('security.totp.preparing') : i18n.t('security.totp.start') }}
                    </button>
                  </div>

                  @if (totpErrorMessage()) { <app-form-message [text]="totpErrorMessage()!" /> }
                </form>
              } @else {
                <div class="totp-setup">
                  <div class="qr-wrap">
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
                        <div class="secret-value">
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
                        <label class="field totp-code-field">
                          <span>{{ i18n.t('auth.totp') }} <span class="required-mark" aria-hidden="true">*</span></span>
                          <input inputmode="numeric" autocomplete="one-time-code" formControlName="code" maxlength="6" required />
                          <app-field-error [text]="totpError(confirmTotpForm.controls.code)" />
                        </label>
                        @if (totpErrorMessage()) {
                          <app-form-message class="totp-code-message" [text]="totpErrorMessage()!" />
                        }
                      </div>
                    </div>

                    <div class="section-actions totp-setup__action">
                      <button class="ui-button ui-button--blue security-action-button" type="submit" [disabled]="confirmTotpForm.invalid || confirmingTotp()">
                        {{ confirmingTotp() ? i18n.t('security.totp.confirming') : i18n.t('security.totp.confirm') }}
                      </button>
                    </div>
                  </form>
                </div>
              }
            }
          </section>
        </div>
      </section>
    }
  `,
  styles: `
    .dialog-backdrop { position: fixed; inset: 0; z-index: 50; background: rgb(0 0 0 / .34); backdrop-filter: blur(2px); }
    .dialog {
      position: fixed; z-index: 51; top: 50%; left: 50%; width: min(760px, calc(100vw - 28px));
      max-height: calc(100dvh - 30px); overflow: auto; transform: translate(-50%, -50%);
      border: 2px solid var(--line-strong); border-radius: var(--radius-card); background: var(--surface); color: var(--text);
      box-shadow: 7px 7px 0 var(--shadow-color);
    }
    .security-dialog {
      --token-accent: var(--blue);
      --token-accent-strong: var(--blue-strong);
      --focus-accent: var(--blue);
    }
    .dialog__header { position: sticky; top: 0; z-index: 2; display: flex; align-items: center; justify-content: space-between; gap: var(--form-gap); padding: 17px 19px; border-bottom: 2px solid var(--line); background: var(--surface); }
    .dialog__title { display: flex; align-items: center; gap: var(--inline-gap); }
    .dialog__title h2 { margin: 0; font-size: 1.22rem; letter-spacing: -.01em; }
    .title-icon { width: 40px; height: 40px; }
    .dialog__body { padding: 0 var(--space-5) 22px; }
    .security-section { padding: var(--section-gap) 0; border-bottom: 1px solid var(--line); }
    .security-section:last-child { border-bottom: 0; padding-bottom: 0; }
    .security-section h3 { margin: 0 0 var(--form-gap); font-size: 1rem; letter-spacing: -.005em; }
    .notice-token { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--form-gap); padding: var(--space-3); border: 2px solid var(--blue-strong); border-radius: 6px; background: var(--blue-soft); font-size: .84rem; font-weight: 650; line-height: 1.35; }
    .notice-token app-icon { flex: 0 0 auto; color: var(--blue-strong); }
    .security-form, .confirm-form { display: grid; gap: var(--form-gap); }
    .password-grid, .form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--form-gap); }
    .password-grid__current { grid-column: 1 / -1; }
    .password-grid--totp .password-grid__current { grid-column: auto; }
    .section-actions { display: flex; justify-content: flex-end; padding-top: 2px; }
    .security-action-button { width: 210px; min-width: 210px; }
    .password-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--form-gap); justify-items: end; }
    .password-actions .security-action-button { grid-column: 2; }
    .totp-form { margin-top: var(--form-gap); }
    .totp-status-state { min-height: 78px; display: flex; align-items: center; justify-content: center; gap: var(--space-3); padding: var(--form-gap); border: 2px solid color-mix(in srgb, var(--blue-strong) 56%, var(--line)); border-radius: var(--radius-card); background: var(--surface); color: var(--text-muted); font-size: .86rem; font-weight: 700; box-shadow: 3px 3px 0 var(--shadow-color); }
    .totp-status-state--error { display: grid; justify-items: end; }
    .totp-status-spinner { width: 18px; height: 18px; border: 2px solid color-mix(in srgb, var(--blue) 28%, var(--line)); border-top-color: var(--blue); border-radius: 50%; animation: totp-spin .7s linear infinite; }
    .totp-status-retry { min-height: 40px; padding-inline: var(--form-gap); }
    @keyframes totp-spin { to { transform: rotate(360deg); } }
    .setup-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; grid-template-rows: auto auto auto; column-gap: var(--form-gap); row-gap: var(--field-gap); align-items: stretch; }
    .setup-row .field { display: contents; }
    .setup-row .field > span { grid-column: 1; grid-row: 1; }
    .setup-row .field > input { grid-column: 1; grid-row: 2; }
    .setup-row .field > app-field-error { grid-column: 1; grid-row: 3; }
    .setup-row .security-action-button { grid-column: 2; grid-row: 2; height: 46px; min-height: 46px; }
    .totp-setup { display: grid; grid-template-columns: minmax(238px, .82fr) minmax(300px, 1.18fr); gap: var(--section-gap); margin-top: var(--section-gap); align-items: stretch; }
    .totp-setup__side { position: relative; min-width: 0; min-height: 100%; display: grid; grid-template-rows: minmax(0, 1fr) auto; gap: var(--form-gap); }
    .totp-setup__fields { grid-row: 1; display: grid; gap: var(--space-12); min-width: 0; align-self: center; }
    .totp-setup__action { grid-row: 2; align-self: end; padding-top: 0; }
    .qr-wrap { box-sizing: border-box; display: grid; place-items: center; min-height: 280px; height: 100%; padding: var(--form-gap); border: 2px solid var(--blue-strong); border-radius: var(--radius-card); background: var(--surface); box-shadow: 4px 4px 0 var(--shadow-color); }
    .qr-wrap img { display: block; width: 220px; height: 220px; max-width: 100%; image-rendering: pixelated; }
    .qr-loading { color: var(--text); font-size: 1.4rem; }
    .secret-block, .totp-code-field { position: relative; display: grid; gap: var(--field-gap); min-width: 0; }
    .secret-block__label, .totp-code-field > span { position: absolute; left: 0; bottom: calc(100% + var(--field-gap)); font-size: .86rem; font-weight: 760; white-space: nowrap; }
    .totp-code-stack { min-width: 0; display: grid; gap: var(--form-gap); }
    .totp-code-field > input { display: block; }
    .totp-code-field > app-field-error { display: block; }
    .totp-code-message { display: block; min-width: 0; }
    .secret-value { display: grid; grid-template-columns: minmax(0, 1fr) 44px 44px; align-items: stretch; min-height: 46px; border: 2px solid var(--blue-strong); border-radius: var(--radius-sm); overflow: hidden; background: var(--surface); box-shadow: 3px 3px 0 var(--shadow-color); }
    .secret-value code { min-width: 0; display: flex; align-items: center; min-height: 42px; padding: var(--space-2) 13px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: .82rem; color: var(--text); }
    .secret-visibility-button, .copy-button { box-sizing: border-box; display: grid; place-items: center; width: 44px; min-width: 44px; height: 100%; min-height: 42px; margin: 0; padding: 0; border: 0; border-left: 2px solid var(--blue-strong); border-radius: 0; font: inherit; line-height: 1; transition: background var(--motion-press) ease, color var(--motion-press) ease; }
    .secret-visibility-button { background: var(--surface); color: var(--text); }
    .copy-button { background: var(--blue); color: #07111f; }
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
      .totp-setup__fields { align-self: stretch; gap: var(--form-gap); }
      .secret-block__label, .totp-code-field > span {
        position: static;
        display: block;
        white-space: normal;
      }
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
      .secret-value { grid-template-columns: minmax(0, 1fr) 44px 44px; }
      .secret-value code { grid-column: auto; }
      .secret-visibility-button, .copy-button { grid-column: auto; width: 44px; min-width: 44px; min-height: 42px; border-top: 0; border-left: 2px solid var(--blue-strong); }
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
  readonly totpSuccessMessage = signal<string | null>(null);
  readonly totpStatus = this.security.totpStatus;
  readonly provisioningUri = signal<string | null>(null);
  readonly totpSecret = signal('');
  readonly qrDataUrl = signal<string | null>(null);
  readonly secretCopied = signal(false);
  readonly secretVisible = signal(false);

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

      if (this.totpStatus() === 'enabled') {
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

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open()) this.requestClose();
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
      error: (error: unknown) => {
        this.totpStatusErrorMessage.set(this.apiErrors.message(error, 'errors.totpStatusFailed'));
      },
    });
  }

  changePassword(): void {
    if (this.passwordForm.invalid || this.passwordMismatch() || this.changingPassword()) return;
    this.changingPassword.set(true);
    this.passwordErrorMessage.set(null);
    const value = this.passwordForm.getRawValue();

    this.security.changePassword({
      current_password: value.current_password,
      new_password: value.new_password,
      totp_code: value.totp_code.trim() || null,
    }).pipe(finalize(() => this.changingPassword.set(false))).subscribe({
      next: () => void this.auth.finishLogout({ passwordChanged: true }),
      error: (error: unknown) => this.passwordErrorMessage.set(this.apiErrors.message(error, 'errors.passwordChangeFailed')),
    });
  }

  startTotpSetup(): void {
    if (this.setupForm.invalid || this.startingTotp()) return;
    this.startingTotp.set(true);
    this.clearTotpMessages();

    this.security.startTotpSetup(this.setupForm.getRawValue()).pipe(finalize(() => this.startingTotp.set(false))).subscribe({
      next: (response) => {
        this.setupForm.reset({ current_password: '' });
        this.provisioningUri.set(response.provisioning_uri);
        this.totpSecret.set(this.extractSecret(response.provisioning_uri));
        void this.renderQrCode(response.provisioning_uri);
      },
      error: (error: unknown) => {
        this.totpErrorMessage.set(this.apiErrors.message(error, 'errors.totpSetupFailed'));
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
        this.totpSuccessMessage.set(this.i18n.t('security.totp.enabled'));
      },
      error: (error: unknown) => this.totpErrorMessage.set(this.apiErrors.message(error, 'errors.totpConfirmFailed')),
    });
  }

  disableTotp(): void {
    if (this.totpStatus() !== 'enabled' || this.disableTotpForm.invalid || this.disablingTotp()) return;
    this.disablingTotp.set(true);
    this.clearTotpMessages();

    this.security.disableTotp(this.disableTotpForm.getRawValue()).pipe(finalize(() => this.disablingTotp.set(false))).subscribe({
      next: () => {
        this.resetTotpFormsAndProvisioning();
        this.totpSuccessMessage.set(this.i18n.t('security.totp.disabled'));
      },
      error: (error: unknown) => {
        this.totpErrorMessage.set(this.apiErrors.message(error, 'errors.totpDisableFailed'));
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
      this.qrDataUrl.set(await toDataURL(provisioningUri, { width: 220, margin: 2, errorCorrectionLevel: 'M' }));
    } catch {
      // The secret remains copyable even if local QR rendering fails.
      this.qrDataUrl.set(null);
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
    this.totpSuccessMessage.set(null);
  }

  private resetTotpFormsAndProvisioning(): void {
    this.setupForm.reset({ current_password: '' });
    this.confirmTotpForm.reset({ code: '' });
    this.disableTotpForm.reset({ current_password: '', code: '' });
    this.provisioningUri.set(null);
    this.totpSecret.set('');
    this.qrDataUrl.set(null);
    this.secretCopied.set(false);
    this.secretVisible.set(false);
  }

  private resetDialog(): void {
    this.passwordForm.reset({ current_password: '', new_password: '', confirm_password: '', totp_code: '' });
    this.passwordErrorMessage.set(null);
    this.totpStatusErrorMessage.set(null);
    this.resetTotpFormsAndProvisioning();
    this.clearTotpMessages();
  }
}
