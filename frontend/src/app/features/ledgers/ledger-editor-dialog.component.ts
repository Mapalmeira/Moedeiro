import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, output, signal, untracked } from '@angular/core';
import { DialogShellComponent } from '../../shared/ui/dialog-shell.component';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { LedgerAppearanceFieldsComponent } from '../../shared/ledger/ledger-appearance-fields.component';
import { entityIconValidator } from '../../shared/ledger/entity-icon-validator';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../core/api/api-error';
import { I18nService } from '../../core/i18n/i18n.service';
import { Ledger, LedgerPayload } from '../../core/ledgers/ledger.models';
import { LedgerService } from '../../core/ledgers/ledger.service';
import { bestContrastingForeground, DEFAULT_LEDGER_APPEARANCE, HEX_COLOR_PATTERN, isHexColor } from '../../shared/ledger/ledger-appearance';
import { LedgerIconComponent } from '../../shared/ledger/ledger-icon.component';
import { FieldErrorComponent } from '../../shared/ui/field-error.component';
import { FormMessageComponent } from '../../shared/ui/form-message.component';
import { IconComponent } from '../../shared/ui/icon.component';

const LEDGER_NAME_MAX_LENGTH = 50;


@Component({
  selector: 'app-ledger-editor-dialog',
  standalone: true,
  imports: [DialogShellComponent, ReactiveFormsModule, FieldErrorComponent, FormMessageComponent, IconComponent, LedgerIconComponent, LedgerAppearanceFieldsComponent],
  template: `
    @if (open()) {
      <app-dialog-shell [ariaLabel]="title()" (dismiss)="requestClose()">

        <div class="dialog">
        <header class="dialog__header ui-dialog-header">
          <div class="dialog__title ui-dialog-title">
            <span class="title-icon title-icon--green"><app-icon [name]="ledger() ? 'LucidePencil' : 'LucidePlus'" size="prominent" /></span>
            <h2>{{ title() }}</h2>
          </div>
          <button class="icon-button icon-button--control ui-action-press" type="button" (click)="requestClose()" [disabled]="saving()"
            [attr.aria-label]="i18n.t('common.close')">
            <app-icon name="LucideX" size="control" />
          </button>
        </header>

        <form [formGroup]="form" (ngSubmit)="save()" novalidate>
          <div class="editor-grid">
            <div class="editor-fields">
              <label class="field">
                <span>{{ i18n.t('ledgers.name') }} <span class="required-mark">*</span></span>
                <input type="text" formControlName="name" autocomplete="off" [attr.maxlength]="nameMaxLength" (input)="setNamePreviewFromEvent($event)" />
                <app-field-error [text]="nameError()" />
              </label>

              <app-ledger-appearance-fields [iconControl]="form.controls.icon" [colorControl]="form.controls.color_code" />
              <app-field-error [text]="colorError()" />
              <app-field-error [text]="iconError()" />
            </div>

            <aside class="preview-panel ui-projected-surface">
              <span class="field-label preview-label">{{ i18n.t('ledgers.editor.preview') }}</span>
              <div class="preview-stage">
                <div class="preview-token-frame ui-projected-surface">
                <div class="preview-token" [style.background]="color()" [style.color]="contrast()">
                  <app-ledger-icon [icon]="previewIcon()" [size]="54" />
                </div>
                </div>
              </div>
              <strong class="preview-name">{{ previewName() }}</strong>
            </aside>
          </div>

          @if (errorMessage()) { <app-form-message [text]="errorMessage()!" /> }

          <footer class="dialog__footer ui-surface-actions">
            <button class="ui-button ui-button--green" type="submit" [disabled]="!canSave()">
              {{ ledger() ? i18n.t('ledgers.editor.save') : i18n.t('ledgers.editor.create') }}
            </button>
          </footer>
        </form>
      </div>
      </app-dialog-shell>
    }
  `,
  styles: `
    .dialog {
      --ui-accent: var(--green); --ui-accent-strong: var(--green-strong);
    }
    form { display: grid; gap: var(--section-gap); padding: var(--space-5); }
    .editor-grid { display: grid; grid-template-columns: minmax(0, 1.42fr) minmax(220px, .78fr); gap: var(--space-6); align-items: stretch; }
    .editor-fields { display: grid; gap: var(--space-4); min-width: 0; align-content: start; }
    .field-label { font-size: var(--control-font-size); font-weight: 780; }
    .preview-panel { position: sticky; top: var(--space-5); align-self: stretch; min-height: 0; margin-top: var(--space-6); display: grid; grid-template-rows: auto minmax(0, 1fr) auto; justify-items: center; gap: var(--space-3); padding: var(--space-4); border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-card); background: var(--surface-muted); }
    .preview-label { justify-self: start; color: var(--text); }
    .preview-stage { width: 100%; min-height: 0; display: grid; place-items: center; align-self: stretch; }
    .preview-token-frame { border-radius: var(--space-3); }
    .preview-token { width: 124px; height: 124px; display: grid; place-items: center; overflow: hidden; border: var(--border-width) solid var(--line-strong); border-radius: inherit; }
    .preview-name { max-width: 100%; overflow-wrap: anywhere; text-align: center; font-size: 1.02rem; }
    .dialog__footer .ui-button { min-width: var(--action-button-min-width); }
    @media (max-width: 760px) {
      .editor-grid { grid-template-columns: 1fr; }
      .preview-panel { position: static; min-height: 220px; margin-top: 0; grid-template-rows: auto minmax(0, 1fr) auto; justify-items: center; align-items: stretch; }
      .preview-token { width: 90px; height: 90px; }
      .preview-name { text-align: center; }
    }
    @media (max-width: 520px) {
      .dialog__footer .ui-button { width: 100%; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerEditorDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly ledgers = inject(LedgerService);
  private readonly apiErrors = inject(ApiErrorService);
  private readonly destroyRef = inject(DestroyRef);
  readonly i18n = inject(I18nService);
  readonly open = input(false);
  readonly ledger = input<Ledger | null>(null);
  readonly close = output<void>();
  readonly saved = output<Ledger>();
  readonly nameMaxLength = LEDGER_NAME_MAX_LENGTH;
  readonly saving = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly color = signal(DEFAULT_LEDGER_APPEARANCE.color);
  readonly previewIcon = signal(DEFAULT_LEDGER_APPEARANCE.icon);
  readonly previewNameValue = signal('');
  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(LEDGER_NAME_MAX_LENGTH)]],
    icon: [DEFAULT_LEDGER_APPEARANCE.icon, [entityIconValidator]],
    color_code: [DEFAULT_LEDGER_APPEARANCE.color, [Validators.required, Validators.pattern(HEX_COLOR_PATTERN)]],
  });
  readonly title = computed(() => this.i18n.t(this.ledger() ? 'ledgers.editor.editTitle' : 'ledgers.editor.createTitle'));
  readonly contrast = computed(() => bestContrastingForeground(this.color()));
  readonly previewName = computed(() => this.previewNameValue().trim() || this.i18n.t('ledgers.editor.previewName'));

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      const raw = this.form.getRawValue();
      this.previewIcon.set(raw.icon);
      this.previewNameValue.set(raw.name);
      if (isHexColor(raw.color_code)) this.color.set(raw.color_code);
    });
    effect(() => {
      const open = this.open(), ledger = this.ledger();
      if (open) untracked(() => {
        this.form.reset({ name: ledger?.name ?? '', icon: ledger?.icon ?? DEFAULT_LEDGER_APPEARANCE.icon, color_code: ledger?.color_code ?? DEFAULT_LEDGER_APPEARANCE.color });
        this.errorMessage.set(null);
      });
    });
  }

  setNamePreviewFromEvent(event: Event): void { this.previewNameValue.set((event.target as HTMLInputElement).value); }
  nameError(): string | null {
    const control = this.form.controls.name;
    if (!control.dirty) return null;
    if (control.hasError('required')) return this.i18n.t('validation.required');
    return control.hasError('maxlength') ? this.i18n.t('validation.ledgerNameMax', { max: LEDGER_NAME_MAX_LENGTH }) : null;
  }
  colorError(): string | null { return this.form.controls.color_code.dirty && this.form.controls.color_code.invalid ? this.i18n.t('validation.ledgerColor') : null; }
  iconError(): string | null { return this.form.controls.icon.dirty && this.form.controls.icon.invalid ? this.i18n.t('validation.ledgerIconUnicode') : null; }
  canSave(): boolean { return !this.saving() && this.form.valid; }
  save(): void {
    if (!this.canSave()) return;
    const raw = this.form.getRawValue();
    const payload: LedgerPayload = { name: raw.name.trim(), icon: raw.icon, color_code: raw.color_code.toUpperCase() };
    if (!payload.name) { this.form.controls.name.setErrors({ required: true }); this.form.controls.name.markAsDirty(); return; }
    this.saving.set(true);
    this.errorMessage.set(null);
    const current = this.ledger();
    const request = current ? this.ledgers.update(current.uuid, payload) : this.ledgers.create(payload);
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving.set(false))).subscribe({
      next: saved => { this.saved.emit(saved); this.close.emit(); },
      error: error => this.errorMessage.set(this.apiErrors.message(error, current ? 'errors.ledgerUpdateFailed' : 'errors.ledgerCreateFailed')),
    });
  }
  requestClose(): void { if (!this.saving()) this.close.emit(); }
}
