import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, output, signal, untracked } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Subject, finalize, takeUntil } from 'rxjs';
import { ApiErrorService } from '../../core/api/api-error';
import { I18nService } from '../../core/i18n/i18n.service';
import { ExternalAccessGrant } from '../../core/ledgers/external-access.models';
import { ExternalAccessService } from '../../core/ledgers/external-access.service';
import { Ledger } from '../../core/ledgers/ledger.models';
import { SecurityService } from '../../core/security/security.service';
import { PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, TOTP_PATTERN } from '../../shared/forms/backend-validators';
import { NoWhitespaceInputDirective } from '../../shared/forms/no-whitespace-input.directive';
import { DialogShellComponent } from '../../shared/ui/dialog-shell.component';
import { FieldErrorComponent } from '../../shared/ui/field-error.component';
import { FormMessageComponent } from '../../shared/ui/form-message.component';
import { IconComponent } from '../../shared/ui/icon.component';

const EXTERNAL_ACCESS_NAME_MAX_LENGTH = 50;
const COPY_FEEDBACK_DURATION_MS = 1_800;

type ExternalAccessView = 'list' | 'create' | 'created' | 'revoke';

@Component({
  selector: 'app-external-access-dialog',
  standalone: true,
  imports: [
    DialogShellComponent,
    ReactiveFormsModule,
    FieldErrorComponent,
    FormMessageComponent,
    IconComponent,
    NoWhitespaceInputDirective,
  ],
  template: `
    @if (open()) {
      @if (ledger()) {
        <app-dialog-shell [ariaLabel]="i18n.t('externalAccess.title')" dialogWidth="var(--dialog-width-standard)" (dismiss)="requestClose()">
          <div class="dialog">
            <header class="dialog__header ui-dialog-header">
              <div class="dialog__title ui-dialog-title">
                <span class="ui-icon-badge ui-icon-badge--dialog ui-icon-badge--blue ui-projected-icon">
                  <app-icon name="LucideKeyRound" size="prominent" />
                </span>
                <h2>{{ i18n.t('externalAccess.title') }}</h2>
              </div>
              <button class="icon-button icon-button--control ui-action-press" type="button" (click)="requestClose()" [disabled]="busy()"
                [attr.aria-label]="i18n.t('common.close')">
                <app-icon name="LucideX" size="control" />
              </button>
            </header>

            <div class="dialog__body">
              @switch (view()) {
                @case ('list') {
                  @if (totpStatusErrorMessage()) {
                    <app-form-message [text]="totpStatusErrorMessage()!" />
                    <div class="retry-row">
                      <button class="ui-button" type="button" (click)="loadTotpStatus()" [disabled]="loadingTotpStatus()">
                        {{ i18n.t('workspace.retry') }}
                      </button>
                    </div>
                  }
                  @if (loadError()) {
                    <app-form-message [text]="loadError()!" />
                    <div class="retry-row">
                      <button class="ui-button" type="button" (click)="loadAccesses()" [disabled]="loading()">
                        {{ i18n.t('workspace.retry') }}
                      </button>
                    </div>
                  } @else if (loading()) {
                    <div class="state-row" role="status">
                      <span class="ui-spinner" aria-hidden="true"></span>
                      <span>{{ i18n.t('externalAccess.loading') }}</span>
                    </div>
                  } @else if (accesses().length === 0) {
                    <div class="empty-state ui-projected-surface">
                      <span class="empty-state__icon ui-icon-badge ui-icon-badge--title ui-projected-icon">
                        <app-icon name="LucideKeyRound" size="badge" />
                      </span>
                      <strong>{{ i18n.t('externalAccess.empty') }}</strong>
                      <span>{{ i18n.t('externalAccess.emptyHint') }}</span>
                    </div>
                  } @else {
                    <div class="access-list ui-card ui-projected-surface" role="list" [attr.aria-label]="i18n.t('externalAccess.title')">
                      @for (access of accesses(); track access.grant_uuid) {
                        <article class="access-row" role="listitem">
                          <span class="access-row__icon ui-icon-badge ui-projected-icon" aria-hidden="true">
                            <app-icon name="LucideKeyRound" size="control" />
                          </span>
                          <div class="access-row__copy">
                            <strong>{{ access.name }}</strong>
                            <span>{{ i18n.t('externalAccess.createdAt', { date: formatCreatedAt(access.created_at) }) }}</span>
                          </div>
                          <button class="icon-button icon-button--danger ui-action-press" type="button" (click)="showRevoke(access)"
                            [disabled]="!totpStatusReady()"
                            [attr.aria-label]="i18n.t('externalAccess.revoke.accessible', { name: access.name })">
                            <app-icon name="LucideTrash2" size="control" />
                          </button>
                        </article>
                      }
                    </div>
                  }

                  <div class="list-toolbar">
                    <button class="ui-button ui-button--blue" type="button" (click)="showCreate()" [disabled]="loading() || !totpStatusReady()">
                      <app-icon name="LucidePlus" size="control" />
                      <span>{{ i18n.t('externalAccess.create.action') }}</span>
                    </button>
                  </div>
                }

                @case ('create') {
                  <section class="panel-stack">
                    <form class="credential-form" [formGroup]="createForm" (ngSubmit)="createAccess()" novalidate>
                      <label class="field">
                        <span>{{ i18n.t('externalAccess.name') }} <span class="required-mark" aria-hidden="true">*</span></span>
                        <input type="text" formControlName="name" autocomplete="off" [attr.maxlength]="nameMaxLength" />
                        <app-field-error [text]="nameError()" />
                      </label>

                      <div class="credential-grid" [class.credential-grid--totp]="requiresTotp()">
                        <label class="field" [class.ui-field-feedback--rejected]="createPasswordRejected()">
                          <span>{{ i18n.t('security.currentPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
                          <input appNoWhitespace type="password" autocomplete="current-password" formControlName="current_password" required
                            (input)="clearCredentialRejections()" (animationend)="clearCredentialRejections()"
                            [attr.aria-invalid]="createPasswordRejected()" [attr.aria-describedby]="createPasswordRejected() ? 'external-create-password-feedback' : null" />
                          <app-field-error [text]="passwordError(createForm.controls.current_password)" />
                          <app-field-error messageId="external-create-password-feedback" [visuallyHidden]="true" [text]="createPasswordFeedback()" />
                        </label>

                        @if (requiresTotp()) {
                          <label class="field" [class.ui-field-feedback--rejected]="createTotpRejected()">
                            <span>{{ i18n.t('auth.totp') }} <span class="required-mark" aria-hidden="true">*</span></span>
                            <input inputmode="numeric" autocomplete="one-time-code" formControlName="totp_code" maxlength="6" required
                              (input)="clearCredentialRejections()" (animationend)="clearCredentialRejections()"
                              [attr.aria-invalid]="createTotpRejected()" [attr.aria-describedby]="createTotpRejected() ? 'external-create-totp-feedback' : null" />
                            <app-field-error [text]="totpError(createForm.controls.totp_code)" />
                            <app-field-error messageId="external-create-totp-feedback" [visuallyHidden]="true" [text]="createTotpFeedback()" />
                          </label>
                        }
                      </div>

                      @if (actionError()) { <app-form-message [text]="actionError()!" /> }

                      <footer class="dialog__footer ui-surface-actions">
                        <button class="ui-button" type="button" (click)="showList()" [disabled]="creating()">{{ i18n.t('externalAccess.cancel') }}</button>
                        <button class="ui-button ui-button--blue" type="submit" [disabled]="createForm.invalid || creating() || !totpStatusReady()">
                          {{ i18n.t('externalAccess.create.action') }}
                        </button>
                      </footer>
                    </form>
                  </section>
                }

                @case ('created') {
                  <section class="panel-stack">
                    <app-form-message kind="warning" [text]="i18n.t('externalAccess.created.warning')" />

                    <div class="token-block">
                      <span class="token-block__label">{{ i18n.t('externalAccess.created.token') }}</span>
                      <div class="token-value">
                        <code>{{ createdToken() }}</code>
                        <button class="copy-button" type="button" (click)="copyToken()"
                          [attr.aria-label]="tokenCopied() ? i18n.t('externalAccess.created.copied') : i18n.t('externalAccess.created.copy')">
                          <app-icon [name]="tokenCopied() ? 'LucideCheck' : 'LucideCopy'" size="control" />
                        </button>
                      </div>
                    </div>

                    <footer class="dialog__footer ui-surface-actions">
                      <button class="ui-button ui-button--blue" type="button" (click)="finishCreated()">
                        {{ i18n.t('externalAccess.created.done') }}
                      </button>
                    </footer>
                  </section>
                }

                @case ('revoke') {
                  @if (selectedAccess()) {
                    <section class="panel-stack">
                      <app-form-message kind="warning" [text]="i18n.t('externalAccess.revoke.warning')" />

                      <form class="credential-form" [formGroup]="revokeForm" (ngSubmit)="revokeAccess()" novalidate>
                        <div class="credential-grid" [class.credential-grid--totp]="requiresTotp()">
                          <label class="field" [class.ui-field-feedback--rejected]="revokePasswordRejected()">
                            <span>{{ i18n.t('security.currentPassword') }} <span class="required-mark" aria-hidden="true">*</span></span>
                            <input appNoWhitespace type="password" autocomplete="current-password" formControlName="current_password" required
                              (input)="clearCredentialRejections()" (animationend)="clearCredentialRejections()"
                              [attr.aria-invalid]="revokePasswordRejected()" [attr.aria-describedby]="revokePasswordRejected() ? 'external-revoke-password-feedback' : null" />
                            <app-field-error [text]="passwordError(revokeForm.controls.current_password)" />
                            <app-field-error messageId="external-revoke-password-feedback" [visuallyHidden]="true" [text]="revokePasswordFeedback()" />
                          </label>

                          @if (requiresTotp()) {
                            <label class="field" [class.ui-field-feedback--rejected]="revokeTotpRejected()">
                              <span>{{ i18n.t('auth.totp') }} <span class="required-mark" aria-hidden="true">*</span></span>
                              <input inputmode="numeric" autocomplete="one-time-code" formControlName="totp_code" maxlength="6" required
                                (input)="clearCredentialRejections()" (animationend)="clearCredentialRejections()"
                                [attr.aria-invalid]="revokeTotpRejected()" [attr.aria-describedby]="revokeTotpRejected() ? 'external-revoke-totp-feedback' : null" />
                              <app-field-error [text]="totpError(revokeForm.controls.totp_code)" />
                              <app-field-error messageId="external-revoke-totp-feedback" [visuallyHidden]="true" [text]="revokeTotpFeedback()" />
                            </label>
                          }
                        </div>

                        @if (actionError()) { <app-form-message [text]="actionError()!" /> }

                        <footer class="dialog__footer ui-surface-actions">
                          <button class="ui-button" type="button" (click)="showList()" [disabled]="revoking()">{{ i18n.t('externalAccess.cancel') }}</button>
                          <button class="ui-button ui-button--danger" type="submit" [disabled]="revokeForm.invalid || revoking() || !totpStatusReady()">
                            {{ i18n.t('externalAccess.revoke.submit') }}
                          </button>
                        </footer>
                      </form>
                    </section>
                  }
                }
              }
            </div>
          </div>
        </app-dialog-shell>
      }
    }
  `,
  styles: `
    .dialog { --ui-accent: var(--blue); --ui-accent-strong: var(--blue-strong); }
    .dialog__body { display: grid; gap: var(--section-gap); padding: var(--space-5); }
    .list-toolbar { display: flex; justify-content: flex-end; }
    .list-toolbar .ui-button { flex: 0 0 auto; padding-inline: var(--space-4); }
    .state-row { min-height: 150px; display: flex; align-items: center; justify-content: center; gap: var(--space-3); color: var(--text-muted); }
    .retry-row { display: flex; justify-content: flex-end; }
    .empty-state { min-height: 170px; display: grid; place-items: center; align-content: center; gap: var(--space-2); padding: var(--space-5); border: var(--border-width) solid var(--line); border-radius: var(--radius-card); background: var(--surface-muted); text-align: center; }
    .empty-state__icon { margin-bottom: var(--space-1); background: var(--blue); color: var(--on-blue); }
    .empty-state > span:last-child { max-width: 420px; color: var(--text-muted); font-size: var(--control-detail-font-size); line-height: 1.4; }
    .access-list { display: grid; overflow: hidden; }
    .access-row { display: grid; grid-template-columns: var(--icon-button-size) minmax(0, 1fr) auto; align-items: center; gap: var(--space-3); min-height: var(--list-row-height); padding: var(--space-2) var(--space-4); border: 0; border-bottom: var(--border-width) solid var(--line); background: var(--surface); }
    .access-row:last-child { border-bottom: 0; }
    .access-row:hover { background: var(--surface-muted); }
    .access-row__icon { --icon-badge-size: var(--icon-button-size); background: var(--blue-soft); color: var(--blue-strong); }
    .access-row__copy { min-width: 0; display: grid; gap: 2px; }
    .access-row__copy strong { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--control-font-size); }
    .access-row__copy span { color: var(--text-muted); font-size: var(--control-detail-font-size); font-variant-numeric: tabular-nums; }
    .panel-stack { display: grid; gap: var(--section-gap); }
    .credential-form { display: grid; gap: var(--form-gap); }
    .credential-grid { display: grid; grid-template-columns: 1fr; gap: var(--form-gap); }
    .credential-grid--totp { grid-template-columns: minmax(0, 1fr) minmax(190px, .52fr); }
    .dialog__footer { padding-top: var(--space-2); }
    .dialog__footer .ui-button { min-width: var(--action-button-min-width); }
    .token-block { min-width: 0; display: grid; gap: var(--field-gap); }
    .token-block__label { font-size: var(--control-font-size); font-weight: 700; }
    .token-value { min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr) var(--menu-item-height); border: var(--border-width) solid var(--blue-strong); border-radius: var(--radius-sm); background: var(--surface); box-shadow: var(--selection-shadow); overflow: hidden; }
    .token-value code { min-width: 0; display: flex; align-items: center; min-height: var(--control-height); padding: var(--space-2) var(--control-padding-inline); overflow-wrap: anywhere; color: var(--text); font-size: .82rem; line-height: 1.4; user-select: all; }
    .copy-button { display: grid; place-items: center; width: var(--menu-item-height); min-width: var(--menu-item-height); min-height: var(--control-height); padding: 0; border: 0; border-left: var(--border-width) solid var(--blue-strong); background: var(--blue); color: var(--on-blue); }
    .copy-button:hover { background: color-mix(in srgb, var(--blue) 88%, var(--on-blue)); }
    @media (max-width: 620px) {
      .dialog__body { padding: var(--space-4); }
      .list-toolbar .ui-button { width: 100%; }
      .credential-grid--totp { grid-template-columns: 1fr; }
      .dialog__footer { display: grid; grid-template-columns: 1fr; }
      .dialog__footer .ui-button { width: 100%; min-width: 0; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExternalAccessDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly externalAccesses = inject(ExternalAccessService);
  private readonly security = inject(SecurityService);
  private readonly apiErrors = inject(ApiErrorService);
  private readonly destroyRef = inject(DestroyRef);
  readonly i18n = inject(I18nService);

  readonly open = input(false);
  readonly ledger = input<Ledger | null>(null);
  readonly close = output<void>();

  readonly nameMaxLength = EXTERNAL_ACCESS_NAME_MAX_LENGTH;
  readonly view = signal<ExternalAccessView>('list');
  readonly accesses = signal<ExternalAccessGrant[]>([]);
  readonly selectedAccess = signal<ExternalAccessGrant | null>(null);
  readonly createdToken = signal('');
  readonly tokenCopied = signal(false);
  readonly loading = signal(false);
  readonly loadingTotpStatus = signal(false);
  readonly creating = signal(false);
  readonly revoking = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly actionError = signal<string | null>(null);
  readonly totpStatusErrorMessage = signal<string | null>(null);
  readonly createPasswordRejected = signal(false);
  readonly createTotpRejected = signal(false);
  readonly revokePasswordRejected = signal(false);
  readonly revokeTotpRejected = signal(false);
  readonly totpRequiredOverride = signal(false);
  readonly requiresTotp = computed(() => this.security.totpStatus() === 'ENABLED' || this.totpRequiredOverride());
  readonly totpStatusReady = computed(() => this.security.totpStatus() !== 'unknown');
  private copyFeedbackTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly dialogReset = new Subject<void>();
  private readonly dateFormatter = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });

  readonly createForm = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(EXTERNAL_ACCESS_NAME_MAX_LENGTH)]],
    current_password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH), Validators.maxLength(PASSWORD_MAX_LENGTH)]],
    totp_code: [''],
  });

  readonly revokeForm = this.fb.nonNullable.group({
    current_password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH), Validators.maxLength(PASSWORD_MAX_LENGTH)]],
    totp_code: [''],
  });

  constructor() {
    effect(() => {
      const open = this.open();
      const ledger = this.ledger();
      if (!open) {
        untracked(() => this.clearCreatedToken());
        return;
      }
      if (ledger) untracked(() => {
        this.resetDialog();
        this.loadAccesses();
        this.loadTotpStatus();
      });
    });

    effect(() => {
      const required = this.requiresTotp();
      untracked(() => {
        for (const control of [this.createForm.controls.totp_code, this.revokeForm.controls.totp_code]) {
          if (required) control.setValidators([Validators.required, Validators.pattern(TOTP_PATTERN)]);
          else {
            control.clearValidators();
            control.setValue('', { emitEvent: false });
          }
          control.updateValueAndValidity({ emitEvent: false });
        }
      });
    });

    this.destroyRef.onDestroy(() => {
      this.clearCopyFeedbackTimer();
      this.dialogReset.next();
      this.dialogReset.complete();
    });
  }

  busy(): boolean {
    return this.creating() || this.revoking();
  }

  loadAccesses(): void {
    const ledger = this.ledger();
    if (!ledger || this.loading()) return;
    this.loading.set(true);
    this.loadError.set(null);
    this.externalAccesses.list(ledger.uuid).pipe(
      takeUntil(this.dialogReset),
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loading.set(false)),
    ).subscribe({
      next: (accesses) => this.accesses.set(accesses),
      error: (error: unknown) => this.loadError.set(this.apiErrors.message(error, 'errors.externalAccessLoadFailed')),
    });
  }

  loadTotpStatus(): void {
    if (this.loadingTotpStatus()) return;
    this.loadingTotpStatus.set(true);
    this.totpStatusErrorMessage.set(null);
    this.security.getTotpStatus().pipe(
      takeUntil(this.dialogReset),
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loadingTotpStatus.set(false)),
    ).subscribe({
      error: (error: unknown) => this.totpStatusErrorMessage.set(this.apiErrors.message(error, 'errors.totpStatusFailed')),
    });
  }

  showCreate(): void {
    if (!this.totpStatusReady()) return;
    this.clearCreatedToken();
    this.selectedAccess.set(null);
    this.createForm.reset({ name: '', current_password: '', totp_code: '' });
    this.actionError.set(null);
    this.clearCredentialRejections();
    this.view.set('create');
  }

  showRevoke(access: ExternalAccessGrant): void {
    if (!this.totpStatusReady()) return;
    this.clearCreatedToken();
    this.selectedAccess.set(access);
    this.revokeForm.reset({ current_password: '', totp_code: '' });
    this.actionError.set(null);
    this.clearCredentialRejections();
    this.view.set('revoke');
  }

  showList(): void {
    if (this.creating() || this.revoking()) return;
    this.clearCreatedToken();
    this.selectedAccess.set(null);
    this.actionError.set(null);
    this.clearCredentialRejections();
    this.view.set('list');
  }

  createAccess(): void {
    const ledger = this.ledger();
    if (!ledger || !this.totpStatusReady() || this.createForm.invalid || this.creating()) return;

    const raw = this.createForm.getRawValue();
    const name = raw.name.trim();
    if (!name) {
      this.createForm.controls.name.setErrors({ required: true });
      this.createForm.controls.name.markAsDirty();
      return;
    }

    this.creating.set(true);
    this.actionError.set(null);
    this.clearCredentialRejections();
    this.externalAccesses.create(ledger.uuid, {
      name,
      current_password: raw.current_password,
      totp_code: this.requiresTotp() ? raw.totp_code : null,
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.creating.set(false)),
    ).subscribe({
      next: (created) => {
        const { token, ...access } = created;
        this.accesses.update((current) => [access, ...current]);
        this.createdToken.set(token);
        this.createForm.reset({ name: '', current_password: '', totp_code: '' });
        this.view.set('created');
      },
      error: (error: unknown) => this.handleCredentialError(error, 'create'),
    });
  }

  revokeAccess(): void {
    const ledger = this.ledger();
    const selected = this.selectedAccess();
    if (!ledger || !selected || !this.totpStatusReady() || this.revokeForm.invalid || this.revoking()) return;

    const raw = this.revokeForm.getRawValue();
    this.revoking.set(true);
    this.actionError.set(null);
    this.clearCredentialRejections();
    this.externalAccesses.revoke(ledger.uuid, selected.grant_uuid, {
      current_password: raw.current_password,
      totp_code: this.requiresTotp() ? raw.totp_code : null,
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.revoking.set(false)),
    ).subscribe({
      next: () => {
        this.accesses.update((current) => current.filter((access) => access.grant_uuid !== selected.grant_uuid));
        this.selectedAccess.set(null);
        this.revokeForm.reset({ current_password: '', totp_code: '' });
        this.view.set('list');
      },
      error: (error: unknown) => this.handleCredentialError(error, 'revoke'),
    });
  }

  finishCreated(): void {
    this.clearCreatedToken();
    this.view.set('list');
  }

  requestClose(): void {
    if (this.busy()) return;
    this.resetDialog();
    this.close.emit();
  }

  nameError(): string | null {
    const control = this.createForm.controls.name;
    if (!this.shouldShowError(control)) return null;
    if (control.hasError('required')) return this.i18n.t('validation.required');
    return control.hasError('maxlength') ? this.i18n.t('externalAccess.validation.nameMax', { max: EXTERNAL_ACCESS_NAME_MAX_LENGTH }) : null;
  }

  passwordError(control: AbstractControl): string | null {
    if (!this.shouldShowError(control)) return null;
    if (control.hasError('minlength')) return this.i18n.t('validation.password.min', { min: PASSWORD_MIN_LENGTH });
    if (control.hasError('maxlength')) return this.i18n.t('validation.password.max', { max: PASSWORD_MAX_LENGTH });
    return null;
  }

  totpError(control: AbstractControl): string | null {
    if (!this.shouldShowError(control)) return null;
    return control.hasError('pattern') ? this.i18n.t('validation.totp.invalid') : null;
  }

  createPasswordFeedback(): string | null {
    return this.createPasswordRejected() ? this.i18n.t('errors.invalidCurrentPassword') : null;
  }

  createTotpFeedback(): string | null {
    return this.createTotpRejected() ? this.i18n.t('feedback.invalidTotpCode') : null;
  }

  revokePasswordFeedback(): string | null {
    return this.revokePasswordRejected() ? this.i18n.t('errors.invalidCurrentPassword') : null;
  }

  revokeTotpFeedback(): string | null {
    return this.revokeTotpRejected() ? this.i18n.t('feedback.invalidTotpCode') : null;
  }

  clearCredentialRejections(): void {
    this.createPasswordRejected.set(false);
    this.createTotpRejected.set(false);
    this.revokePasswordRejected.set(false);
    this.revokeTotpRejected.set(false);
  }

  formatCreatedAt(timestamp: number): string {
    return this.dateFormatter.format(new Date(timestamp * 1000));
  }

  async copyToken(): Promise<void> {
    const token = this.createdToken();
    if (!token) return;

    try {
      await navigator.clipboard.writeText(token);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = token;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      textarea.remove();
    }

    this.tokenCopied.set(true);
    this.clearCopyFeedbackTimer();
    this.copyFeedbackTimer = setTimeout(() => {
      this.tokenCopied.set(false);
      this.copyFeedbackTimer = null;
    }, COPY_FEEDBACK_DURATION_MS);
  }

  private handleCredentialError(error: unknown, target: 'create' | 'revoke'): void {
    if (this.hasErrorDetail(error, 'Invalid current password')) {
      target === 'create' ? this.createPasswordRejected.set(true) : this.revokePasswordRejected.set(true);
      return;
    }
    if (this.hasErrorDetail(error, 'Invalid TOTP code')) {
      target === 'create' ? this.createTotpRejected.set(true) : this.revokeTotpRejected.set(true);
      return;
    }
    if (this.hasErrorDetail(error, 'TOTP required')) {
      this.totpRequiredOverride.set(true);
      this.actionError.set(this.i18n.t('errors.totpRequired'));
      return;
    }
    this.actionError.set(this.apiErrors.message(error, target === 'create' ? 'errors.externalAccessCreateFailed' : 'errors.externalAccessRevokeFailed'));
  }

  private hasErrorDetail(error: unknown, detail: string): boolean {
    return error instanceof HttpErrorResponse && error.error?.detail === detail;
  }

  private shouldShowError(control: AbstractControl): boolean {
    return control.invalid && control.dirty;
  }

  private resetDialog(): void {
    this.dialogReset.next();
    this.view.set('list');
    this.accesses.set([]);
    this.selectedAccess.set(null);
    this.clearCreatedToken();
    this.loading.set(false);
    this.loadingTotpStatus.set(false);
    this.creating.set(false);
    this.revoking.set(false);
    this.loadError.set(null);
    this.actionError.set(null);
    this.totpStatusErrorMessage.set(null);
    this.totpRequiredOverride.set(false);
    this.clearCredentialRejections();
    this.createForm.reset({ name: '', current_password: '', totp_code: '' });
    this.revokeForm.reset({ current_password: '', totp_code: '' });
  }

  private clearCreatedToken(): void {
    this.createdToken.set('');
    this.tokenCopied.set(false);
    this.clearCopyFeedbackTimer();
  }

  private clearCopyFeedbackTimer(): void {
    if (this.copyFeedbackTimer !== null) {
      clearTimeout(this.copyFeedbackTimer);
      this.copyFeedbackTimer = null;
    }
  }
}
