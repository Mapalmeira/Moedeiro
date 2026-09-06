import { ChangeDetectionStrategy, Component, HostListener, computed, effect, inject, input, output, signal, untracked } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../core/api/api-error';
import { I18nService } from '../../core/i18n/i18n.service';
import { Ledger, LedgerPayload } from '../../core/ledgers/ledger.models';
import { LedgerService } from '../../core/ledgers/ledger.service';
import { bestContrastingForeground } from '../../shared/ledger/ledger-appearance';
import { LedgerIconComponent } from '../../shared/ledger/ledger-icon.component';
import { decodeLucideLedgerIcon, decodeUnicodeLedgerIcon, encodeLucideLedgerIcon, encodeUnicodeLedgerIcon, isEncodedLucideLedgerIcon, isEncodedUnicodeLedgerIcon } from '../../shared/ledger/ledger-icon-value';
import { LUCIDE_ICON_CATALOG, resolveLucideIcon } from '../../shared/ledger/lucide-icon-catalog';
import { FieldErrorComponent } from '../../shared/ui/field-error.component';
import { FormMessageComponent } from '../../shared/ui/form-message.component';
import { IconComponent } from '../../shared/ui/icon.component';

const LEDGER_NAME_MAX_LENGTH = 50;
const COLOR_PATTERN = /^#[0-9A-Fa-f]{6}$/;
const DEFAULT_ICON = 'lucide:WalletCards';
const DEFAULT_COLOR = '#21E683';
const ICON_RESULT_LIMIT = 160;

type IconMode = 'lucide' | 'unicode';

@Component({
  selector: 'app-ledger-editor-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, FieldErrorComponent, FormMessageComponent, IconComponent, LedgerIconComponent],
  template: `
    @if (open()) {
      <div class="dialog-backdrop" (click)="requestClose()" aria-hidden="true"></div>
      <section class="dialog" role="dialog" aria-modal="true" [attr.aria-label]="title()">
        <header class="dialog__header">
          <div class="dialog__title">
            <span class="title-icon"><app-icon [name]="ledger() ? 'pencil' : 'plus'" [size]="25" /></span>
            <h2>{{ title() }}</h2>
          </div>
          <button class="icon-button" type="button" (click)="requestClose()" [disabled]="saving()"
            [attr.aria-label]="i18n.t('common.close')">
            <app-icon name="x" [size]="19" />
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

              <section class="appearance-field">
                <span class="field-label">{{ i18n.t('ledgers.editor.color') }}</span>
                <div class="color-row">
                  <input class="color-picker" type="color" [value]="color()" (input)="setColorFromEvent($event)"
                    [attr.aria-label]="i18n.t('ledgers.editor.color')" />
                  <label class="field color-code-field">
                    <input type="text" formControlName="color_code" maxlength="7" autocomplete="off"
                      (input)="setColorTextFromEvent($event)" aria-label="Hex" />
                  </label>
                </div>
                <app-field-error [text]="colorError()" />
              </section>

              <section class="appearance-field icon-field">
                <span class="field-label">{{ i18n.t('ledgers.editor.icon') }}</span>
                <div class="mode-switch" role="group" [attr.aria-label]="i18n.t('ledgers.editor.icon')">
                  <button type="button" class="ui-choice mode-switch__button" [class.ui-choice--selected]="iconMode() === 'lucide'" (click)="setIconMode('lucide')">Lucide</button>
                  <button type="button" class="ui-choice mode-switch__button" [class.ui-choice--selected]="iconMode() === 'unicode'" (click)="setIconMode('unicode')">Unicode</button>
                </div>

                <div class="icon-control-slot">
                  @if (iconMode() === 'lucide') {
                    <div class="lucide-picker">
                      <button type="button" class="lucide-picker__trigger ui-select-trigger" (click)="toggleIconPicker()"
                        [attr.aria-expanded]="iconPickerOpen()" [attr.aria-label]="i18n.t('ledgers.editor.icon')">
                        <span class="lucide-picker__selected-icon"><app-ledger-icon [icon]="form.controls.icon.value" [size]="22" /></span>
                        <span class="lucide-picker__selected-label">{{ selectedLucideLabel() }}</span>
                        <app-icon class="ui-select-chevron" name="chevron-down" [size]="17" />
                      </button>

                      @if (iconPickerOpen()) {
                        <div class="lucide-picker__panel ui-dropdown-panel">
                          <label class="icon-search ui-dropdown-search">
                            <app-icon name="search" [size]="18" />
                            <input type="search" [value]="iconSearch()" (input)="setIconSearchFromEvent($event)"
                              [attr.aria-label]="i18n.t('ledgers.editor.icon')" autofocus />
                          </label>
                          <div class="icon-grid" role="listbox" [attr.aria-label]="i18n.t('ledgers.editor.icon')">
                            @for (entry of visibleIcons(); track entry.id) {
                              <button type="button" class="ui-choice icon-choice" role="option" [attr.aria-selected]="selectedLucideId() === entry.id"
                                [class.ui-choice--selected]="selectedLucideId() === entry.id" (click)="selectLucideIcon(entry.id)"
                                [title]="entry.label">
                                <app-ledger-icon [icon]="'lucide:' + entry.id" [size]="22" />
                                <span>{{ entry.label }}</span>
                              </button>
                            }
                          </div>
                        </div>
                      }
                    </div>
                  } @else {
                    <label class="field unicode-field">
                      <input type="text" [value]="form.controls.icon.value" autocomplete="off"
                        (input)="setUnicodeIconFromEvent($event)" [placeholder]="i18n.t('ledgers.editor.unicode')" />
                    </label>
                  }
                </div>
                <app-field-error [text]="iconError()" />
              </section>
            </div>

            <aside class="preview-panel">
              <span class="field-label preview-label">{{ i18n.t('ledgers.editor.preview') }}</span>
              <div class="preview-stage">
                <div class="preview-token" [style.background]="color()" [style.color]="contrast().foreground">
                  <app-ledger-icon [icon]="previewIcon()" [size]="54" />
                </div>
              </div>
              <strong class="preview-name">{{ previewName() }}</strong>
            </aside>
          </div>

          @if (errorMessage()) { <app-form-message [text]="errorMessage()!" /> }

          <footer class="dialog__footer">
            <button class="ui-button ui-button--green" type="submit" [disabled]="!canSave()">
              {{ saving() ? i18n.t('ledgers.editor.saving') : (ledger() ? i18n.t('ledgers.editor.save') : i18n.t('ledgers.editor.create')) }}
            </button>
          </footer>
        </form>
      </section>
    }
  `,
  styles: `
    .dialog-backdrop { position: fixed; inset: 0; z-index: 50; background: rgb(0 0 0 / .34); backdrop-filter: blur(2px); }
    .dialog {
      --token-accent: var(--green); --token-accent-strong: var(--green-strong); --focus-accent: var(--green);
      position: fixed; z-index: 51; top: 50%; left: 50%; width: min(760px, calc(100vw - 28px));
      max-height: calc(100dvh - 30px); overflow: auto; transform: translate(-50%, -50%);
      border: 2px solid var(--line-strong); border-radius: var(--radius-card); background: var(--surface); color: var(--text);
      filter: var(--dialog-shadow);
    }
    .dialog__header { display: flex; align-items: center; justify-content: space-between; gap: var(--form-gap); padding: 17px 19px; border-bottom: 2px solid var(--line); }
    .dialog__title { display: flex; align-items: center; gap: var(--title-icon-gap); }
    .dialog__title h2 { margin: 0; font-size: 1.22rem; letter-spacing: -.01em; }
    .title-icon { width: 46px; height: 46px; display: grid; place-items: center; flex: 0 0 46px; border: 2px solid var(--line-strong); border-radius: 5px; background: var(--green); color: #060606; }
    form { display: grid; gap: var(--section-gap); padding: var(--space-5); }
    .editor-grid { display: grid; grid-template-columns: minmax(0, 1.42fr) minmax(220px, .78fr); gap: var(--space-6); align-items: stretch; }
    .editor-fields { display: grid; gap: var(--space-4); min-width: 0; align-content: start; }
    .appearance-field { display: grid; gap: var(--field-gap); min-width: 0; }
    .field-label { font-size: .9rem; font-weight: 780; }
    .color-row { display: grid; grid-template-columns: 70px minmax(0, 1fr); gap: var(--space-3); align-items: stretch; }
    .color-picker { box-sizing: border-box; width: 70px; height: 46px; padding: 4px; border: 2px solid var(--line-strong); border-radius: var(--radius-sm); outline: none; background: var(--surface); box-shadow: none; }
    .color-picker:focus, .color-picker:focus-visible { border-color: var(--green-strong); outline: none; box-shadow: 0 0 0 3px color-mix(in srgb, var(--green) 32%, transparent); }
    .color-picker::-webkit-color-swatch-wrapper { padding: 0; }
    .color-picker::-webkit-color-swatch { border: 0; border-radius: 3px; }
    .color-picker::-moz-color-swatch { border: 0; border-radius: 3px; }
    .color-code-field { gap: 0; }
    .mode-switch { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-2); }
    .mode-switch__button { width: 100%; min-height: 46px; font-weight: 760; }
    .icon-control-slot { position: relative; min-height: 46px; margin-top: var(--space-2); }
    .lucide-picker { position: relative; }
    .lucide-picker__trigger { width: 100%; height: 46px; display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; align-items: center; gap: var(--space-2); padding: 0 var(--space-3) 0 var(--space-2); text-align: left; font-weight: 650; }
    .lucide-picker__selected-icon { width: 32px; height: 32px; display: grid; place-items: center; overflow: hidden; border: 1.5px solid var(--line-strong); border-radius: 5px; background: var(--surface-muted); }
    .lucide-picker__selected-label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .lucide-picker__panel { position: absolute; z-index: 70; left: 0; right: 0; bottom: calc(100% + var(--space-2)); }
    .icon-grid { max-height: min(196px, 28dvh); overflow: auto; overscroll-behavior: contain; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-2); padding: var(--space-1); }
    .icon-choice { min-width: 0; min-height: 68px; display: grid; justify-items: center; align-content: center; gap: var(--space-1); padding: var(--space-2); }
    .icon-choice span { width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .7rem; font-weight: 680; }
    .unicode-field { gap: 0; }
    .unicode-field input { font-size: .96rem; line-height: 1.2; text-align: center; }
    .unicode-field input::placeholder { color: var(--text-muted); font-size: .8rem; font-weight: 560; }
    .preview-panel { position: sticky; top: var(--space-5); align-self: stretch; min-height: 0; margin-top: var(--space-6); display: grid; grid-template-rows: auto minmax(0, 1fr) auto; justify-items: center; gap: var(--space-3); padding: var(--space-4); border: 2px solid var(--line-strong); border-radius: var(--radius-card); background: var(--surface-muted); filter: var(--surface-shadow); }
    .preview-label { justify-self: start; color: var(--text); }
    .preview-stage { width: 100%; min-height: 0; display: grid; place-items: center; align-self: stretch; }
    .preview-token { width: 124px; height: 124px; display: grid; place-items: center; overflow: hidden; border: 2px solid var(--line-strong); border-radius: 12px; filter: var(--surface-shadow); }
    .preview-name { max-width: 100%; overflow-wrap: anywhere; text-align: center; font-size: 1.02rem; }
    .dialog__footer { display: flex; justify-content: flex-end; padding-top: var(--space-1); }
    .dialog__footer .ui-button { min-width: 190px; }
    @media (max-width: 760px) {
      .editor-grid { grid-template-columns: 1fr; }
      .preview-panel { position: static; min-height: 220px; margin-top: 0; grid-template-rows: auto minmax(0, 1fr) auto; justify-items: center; align-items: stretch; }
      .preview-token { width: 90px; height: 90px; }
      .preview-name { text-align: center; }
    }
    @media (max-width: 520px) {
      .icon-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .dialog__footer .ui-button { width: 100%; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerEditorDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly ledgers = inject(LedgerService);
  private readonly apiErrors = inject(ApiErrorService);
  readonly i18n = inject(I18nService);

  readonly open = input(false);
  readonly ledger = input<Ledger | null>(null);
  readonly close = output<void>();
  readonly saved = output<Ledger>();

  readonly nameMaxLength = LEDGER_NAME_MAX_LENGTH;
  readonly saving = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly iconMode = signal<IconMode>('lucide');
  readonly iconSearch = signal('');
  readonly iconPickerOpen = signal(false);
  readonly color = signal(DEFAULT_COLOR);
  readonly previewIcon = signal(DEFAULT_ICON);
  readonly previewNameValue = signal('');

  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(LEDGER_NAME_MAX_LENGTH)]],
    icon: [DEFAULT_ICON, [Validators.required, Validators.maxLength(100)]],
    color_code: [DEFAULT_COLOR, [Validators.required, Validators.pattern(COLOR_PATTERN)]],
  });

  readonly title = computed(() => this.ledger() ? this.i18n.t('ledgers.editor.editTitle') : this.i18n.t('ledgers.editor.createTitle'));
  readonly contrast = computed(() => bestContrastingForeground(this.color()));
  readonly previewName = computed(() => this.previewNameValue().trim() || this.i18n.t('ledgers.editor.previewName'));

  readonly matchingIcons = computed(() => {
    const query = this.iconSearch().trim().toLocaleLowerCase();
    if (!query) return LUCIDE_ICON_CATALOG;
    return LUCIDE_ICON_CATALOG.filter((entry) =>
      entry.label.toLocaleLowerCase().includes(query) || entry.id.toLocaleLowerCase().includes(query.replaceAll(' ', '')),
    );
  });
  readonly visibleIcons = computed(() => this.matchingIcons().slice(0, ICON_RESULT_LIMIT));
  readonly selectedLucideId = computed(() => decodeLucideLedgerIcon(this.previewIcon()));
  readonly selectedLucideLabel = computed(() => {
    const selected = this.selectedLucideId();
    return LUCIDE_ICON_CATALOG.find((entry) => entry.id === selected)?.label ?? selected;
  });

  constructor() {
    effect(() => {
      const isOpen = this.open();
      const ledger = this.ledger();
      if (isOpen) untracked(() => this.resetFor(ledger));
    });
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.iconPickerOpen()) {
      this.iconPickerOpen.set(false);
      return;
    }
    if (this.open()) this.requestClose();
  }

  @HostListener('document:mousedown', ['$event'])
  closeIconPickerWhenClickingOutside(event: MouseEvent): void {
    if (!this.iconPickerOpen()) return;
    const target = event.target as Element | null;
    if (!target?.closest('.lucide-picker')) this.iconPickerOpen.set(false);
  }

  toggleIconPicker(): void {
    this.iconPickerOpen.update((open) => !open);
    if (this.iconPickerOpen()) this.iconSearch.set('');
  }

  setIconMode(mode: IconMode): void {
    this.iconPickerOpen.set(false);
    this.iconMode.set(mode);
    this.iconSearch.set('');
    this.errorMessage.set(null);
    if (mode === 'lucide' && !resolveLucideIcon(decodeLucideLedgerIcon(this.form.controls.icon.value))) {
      this.form.controls.icon.setValue(DEFAULT_ICON);
      this.previewIcon.set(DEFAULT_ICON);
    } else if (mode === 'unicode' && isEncodedLucideLedgerIcon(this.form.controls.icon.value)) {
      this.form.controls.icon.setValue('💰');
      this.previewIcon.set(encodeUnicodeLedgerIcon('💰'));
    }
    this.form.controls.icon.markAsDirty();
  }

  selectLucideIcon(icon: string): void {
    const encodedIcon = encodeLucideLedgerIcon(icon);
    this.form.controls.icon.setValue(encodedIcon);
    this.form.controls.icon.markAsDirty();
    this.previewIcon.set(encodedIcon);
    this.iconPickerOpen.set(false);
    this.iconSearch.set('');
  }

  setNamePreviewFromEvent(event: Event): void {
    this.previewNameValue.set((event.target as HTMLInputElement).value);
  }

  setIconSearchFromEvent(event: Event): void {
    this.iconSearch.set((event.target as HTMLInputElement).value);
  }

  setUnicodeIconFromEvent(event: Event): void {
    const input = event.target as HTMLInputElement;
    const value = Array.from(input.value).slice(0, 3).join('');
    if (input.value !== value) input.value = value;
    this.form.controls.icon.setValue(value);
    this.form.controls.icon.markAsDirty();
    this.previewIcon.set(encodeUnicodeLedgerIcon(value));
  }

  setColorFromEvent(event: Event): void {
    const value = (event.target as HTMLInputElement).value.toUpperCase();
    this.form.controls.color_code.setValue(value);
    this.form.controls.color_code.markAsDirty();
    this.color.set(value);
  }

  setColorTextFromEvent(event: Event): void {
    const value = (event.target as HTMLInputElement).value.toUpperCase();
    this.form.controls.color_code.setValue(value, { emitEvent: false });
    this.form.controls.color_code.markAsDirty();
    if (COLOR_PATTERN.test(value)) this.color.set(value);
  }

  nameError(): string | null {
    const control = this.form.controls.name;
    if (!control.dirty) return null;
    if (control.hasError('required')) return this.i18n.t('validation.required');
    if (control.hasError('maxlength')) return this.i18n.t('validation.ledgerNameMax', { max: LEDGER_NAME_MAX_LENGTH });
    return null;
  }

  colorError(): string | null {
    const control = this.form.controls.color_code;
    if (!control.dirty) return null;
    if (control.hasError('required')) return this.i18n.t('validation.required');
    if (control.hasError('pattern')) return this.i18n.t('validation.ledgerColor');
    return null;
  }

  iconError(): string | null {
    if (this.iconMode() !== 'unicode') return null;
    const value = this.form.controls.icon.value;
    if (!value) return this.i18n.t('validation.required');
    if (!this.unicodeIconValid(value)) return this.i18n.t('validation.ledgerIconUnicode');
    return null;
  }

  canSave(): boolean {
    return !this.saving() && this.form.valid && this.iconValid();
  }

  save(): void {
    if (!this.canSave()) return;

    const raw = this.form.getRawValue();
    const payload: LedgerPayload = {
      name: raw.name.trim(),
      icon: this.iconMode() === 'unicode' ? encodeUnicodeLedgerIcon(raw.icon) : raw.icon,
      color_code: raw.color_code.toUpperCase(),
    };
    if (!payload.name) {
      this.form.controls.name.setErrors({ required: true });
      this.form.controls.name.markAsDirty();
      return;
    }

    this.saving.set(true);
    this.errorMessage.set(null);
    const current = this.ledger();
    const request = current ? this.ledgers.update(current.uuid, payload) : this.ledgers.create(payload);

    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (saved) => {
        this.saved.emit(saved);
        this.close.emit();
      },
      error: (error: unknown) => this.errorMessage.set(this.apiErrors.message(error, current ? 'errors.ledgerUpdateFailed' : 'errors.ledgerCreateFailed')),
    });
  }

  requestClose(): void {
    if (this.saving()) return;
    this.close.emit();
  }

  private iconValid(): boolean {
    const value = this.form.controls.icon.value;
    return this.iconMode() === 'lucide' ? isEncodedLucideLedgerIcon(value) && resolveLucideIcon(decodeLucideLedgerIcon(value)) !== null : this.unicodeIconValid(value);
  }

  private unicodeIconValid(value: string): boolean {
    const length = Array.from(value).length;
    return length >= 1 && length <= 3;
  }

  private resetFor(ledger: Ledger | null): void {
    const storedIcon = ledger?.icon ?? DEFAULT_ICON;
    const color = (ledger?.color_code ?? DEFAULT_COLOR).toUpperCase();
    const encodedUnicode = isEncodedUnicodeLedgerIcon(storedIcon);
    const encodedLucide = isEncodedLucideLedgerIcon(storedIcon);
    const mode: IconMode = encodedLucide ? 'lucide' : 'unicode';
    const editorIcon = mode === 'unicode' ? decodeUnicodeLedgerIcon(storedIcon) : storedIcon;

    this.form.reset({
      name: ledger?.name ?? '',
      icon: editorIcon || (encodedUnicode ? '💰' : DEFAULT_ICON),
      color_code: color,
    });
    this.iconMode.set(mode);
    this.iconPickerOpen.set(false);
    this.iconSearch.set('');
    this.color.set(COLOR_PATTERN.test(color) ? color : DEFAULT_COLOR);
    this.previewIcon.set(mode === 'unicode' ? encodeUnicodeLedgerIcon(editorIcon || '💰') : storedIcon || DEFAULT_ICON);
    this.previewNameValue.set(ledger?.name ?? '');
    this.errorMessage.set(null);
  }
}
