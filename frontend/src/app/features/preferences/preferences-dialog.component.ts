import { ChangeDetectionStrategy, Component, HostListener, effect, inject, input, output, signal, untracked } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ApiErrorService } from '../../core/api/api-error';
import { AppLanguage, I18nService } from '../../core/i18n/i18n.service';
import { BackendTheme, UserPreferences } from '../../core/preferences/preferences.models';
import { PreferenceDefaultsService } from '../../core/preferences/preference-defaults.service';
import { PreferencesService } from '../../core/preferences/preferences.service';
import { ThemeService, UiTheme } from '../../core/theme/theme.service';
import { IANA_TIMEZONES } from '../../shared/data/iana-timezones';
import { FormMessageComponent } from '../../shared/ui/form-message.component';
import { IconComponent } from '../../shared/ui/icon.component';
import { LanguageSelectorComponent } from '../../shared/ui/language-selector.component';
import { SearchSelectComponent } from '../../shared/ui/search-select.component';

@Component({
  selector: 'app-preferences-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, FormMessageComponent, IconComponent, LanguageSelectorComponent, SearchSelectComponent],
  template: `
    @if (open()) {
      <div class="dialog-backdrop" (click)="requestClose()" aria-hidden="true"></div>
      <section class="dialog" role="dialog" aria-modal="true" [attr.aria-label]="i18n.t('preferences.title')">
        <header class="dialog__header">
          <div class="dialog__title">
            <span class="title-icon title-icon--green"><app-icon name="sliders" [size]="21" /></span>
            <h2>{{ i18n.t('preferences.title') }}</h2>
          </div>
          <button class="icon-button" type="button" (click)="requestClose()" [disabled]="closing() || saving()"
            [attr.aria-label]="i18n.t('common.close')">
            <app-icon name="x" [size]="19" />
          </button>
        </header>

        <form [formGroup]="form" (ngSubmit)="save()" novalidate>
            <div class="preference-grid preference-grid--top">
              <section class="preference-field">
                <span class="preference-label">{{ i18n.t('common.language') }}</span>
                <app-language-selector appearance="field" [value]="form.controls.language.value" (valueChange)="setLanguage($event)" />
              </section>

              <section class="preference-field">
                <span class="preference-label">{{ i18n.t('common.theme') }}</span>
                <div class="choice-grid choice-grid--2">
                  <button type="button" class="ui-choice choice-card choice-card--with-icon"
                    [class.ui-choice--selected]="form.controls.theme.value === 'LIGHT'"
                    (click)="setTheme('LIGHT')">
                    <app-icon name="sun" [size]="18" /><span>{{ i18n.t('theme.light') }}</span>
                  </button>
                  <button type="button" class="ui-choice choice-card choice-card--with-icon"
                    [class.ui-choice--selected]="form.controls.theme.value === 'DARK'"
                    (click)="setTheme('DARK')">
                    <app-icon name="moon" [size]="18" /><span>{{ i18n.t('theme.dark') }}</span>
                  </button>
                </div>
              </section>
            </div>

            <section class="preference-field">
              <span class="preference-label">{{ i18n.t('preferences.dateFormat') }}</span>
              <div class="choice-grid choice-grid--3">
                <button type="button" class="ui-choice choice-card choice-card--example" [class.ui-choice--selected]="form.controls.date_format.value === 'DMY'" (click)="form.controls.date_format.setValue('DMY')">31/12/2026</button>
                <button type="button" class="ui-choice choice-card choice-card--example" [class.ui-choice--selected]="form.controls.date_format.value === 'MDY'" (click)="form.controls.date_format.setValue('MDY')">12/31/2026</button>
                <button type="button" class="ui-choice choice-card choice-card--example" [class.ui-choice--selected]="form.controls.date_format.value === 'YMD'" (click)="form.controls.date_format.setValue('YMD')">2026/12/31</button>
              </div>
            </section>

            <div class="preference-grid">
              <section class="preference-field">
                <span class="preference-label">{{ i18n.t('preferences.timeFormat') }}</span>
                <div class="choice-grid choice-grid--2">
                  <button type="button" class="ui-choice choice-card choice-card--example" [class.ui-choice--selected]="form.controls.time_format.value === 'H12'" (click)="form.controls.time_format.setValue('H12')">07:45 PM</button>
                  <button type="button" class="ui-choice choice-card choice-card--example" [class.ui-choice--selected]="form.controls.time_format.value === 'H24'" (click)="form.controls.time_format.setValue('H24')">19:45</button>
                </div>
              </section>

              <section class="preference-field">
                <span class="preference-label">{{ i18n.t('preferences.numberFormat') }}</span>
                <div class="choice-grid choice-grid--2">
                  <button type="button" class="ui-choice choice-card choice-card--example" [class.ui-choice--selected]="form.controls.number_format.value === 'COMMA'" (click)="form.controls.number_format.setValue('COMMA')">1.234,56</button>
                  <button type="button" class="ui-choice choice-card choice-card--example" [class.ui-choice--selected]="form.controls.number_format.value === 'DOT'" (click)="form.controls.number_format.setValue('DOT')">1,234.56</button>
                </div>
              </section>
            </div>

            <section class="preference-field">
              <span class="preference-label">{{ i18n.t('preferences.timezone') }}</span>
              <app-search-select
                [options]="timezoneOptions"
                [value]="form.controls.timezone.value"
                [ariaLabel]="i18n.t('preferences.timezone')"
                [emptyText]="i18n.t('preferences.timezoneNoResults')"
                openDirection="up"
                (valueChange)="setTimezone($event)" />
            </section>

            @if (errorMessage()) { <app-form-message [text]="errorMessage()!" /> }

            <footer class="dialog__footer">
              <button class="ui-button ui-button--green" type="submit" [disabled]="form.invalid || saving() || closing()">
                {{ saving() ? i18n.t('preferences.saving') : i18n.t('preferences.save') }}
              </button>
            </footer>
        </form>
      </section>
    }
  `,
  styles: `
    .dialog-backdrop { position: fixed; inset: 0; z-index: 40; background: rgb(0 0 0 / .34); backdrop-filter: blur(2px); }
    .dialog {
      position: fixed; z-index: 41; top: 50%; left: 50%; width: min(760px, calc(100vw - 28px));
      max-height: calc(100dvh - 30px); overflow: auto; transform: translate(-50%, -50%);
      border: 2px solid var(--line-strong); border-radius: var(--radius-card); background: var(--surface); color: var(--text);
      box-shadow: 7px 7px 0 var(--shadow-color);
    }
    .dialog__header { display: flex; align-items: center; justify-content: space-between; gap: var(--form-gap); padding: 17px 19px; border-bottom: 2px solid var(--line); }
    .dialog__title { display: flex; align-items: center; gap: var(--title-icon-gap); }
    .dialog__title h2 { margin: 0; font-size: 1.22rem; letter-spacing: -.01em; }
    .dialog__title .title-icon { width: 40px; height: 40px; }
    form { display: grid; gap: 0; padding: 0 var(--space-5) var(--space-5); }
    .preference-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--section-gap); padding: var(--section-gap) 0; border-bottom: 1px solid var(--line); }
    .preference-grid--top { align-items: start; }
    .preference-field { min-width: 0; display: grid; gap: var(--field-gap); padding: var(--section-gap) 0; border-bottom: 1px solid var(--line); }
    .preference-grid .preference-field { padding: 0; border: 0; }
    .preference-label { font-size: .9rem; font-weight: 780; letter-spacing: -.005em; }
    .choice-grid { display: grid; gap: var(--space-2); }
    .choice-grid--2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .choice-grid--3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .choice-card--with-icon { justify-content: flex-start; padding-left: var(--form-gap); }
    .choice-card--example { font-variant-numeric: tabular-nums; letter-spacing: .01em; }
    .dialog__footer { display: flex; justify-content: flex-end; padding-top: var(--section-gap); }
    .dialog__footer .ui-button { min-width: 200px; }
    @media (max-width: 650px) {
      .preference-grid { grid-template-columns: 1fr; }
      .choice-grid--3 { grid-template-columns: 1fr; }
    }
    @media (max-width: 420px) {
      .choice-grid--2 { grid-template-columns: 1fr; }
      .dialog__footer .ui-button { width: 100%; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PreferencesDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly preferences = inject(PreferencesService);
  private readonly preferenceDefaults = inject(PreferenceDefaultsService);
  private readonly theme = inject(ThemeService);
  private readonly apiErrors = inject(ApiErrorService);
  readonly i18n = inject(I18nService);

  readonly open = input(false);
  readonly close = output<void>();
  readonly saving = signal(false);
  readonly closing = signal(false);
  readonly errorMessage = signal<string | null>(null);

  private readonly initialPreferences = this.preferenceDefaults.infer();
  readonly browserTimezone = this.initialPreferences.timezone;
  readonly timezoneOptions = this.buildTimezoneOptions();
  private lastServerPreferences: UserPreferences = this.initialPreferences;
  private committedTheme: UiTheme = this.theme.theme();
  private committedLanguage: AppLanguage = this.i18n.language();

  readonly form = this.fb.group({
    language: this.fb.nonNullable.control(this.initialPreferences.language, Validators.required),
    date_format: this.fb.nonNullable.control(this.initialPreferences.date_format, Validators.required),
    time_format: this.fb.nonNullable.control(this.initialPreferences.time_format, Validators.required),
    number_format: this.fb.nonNullable.control(this.initialPreferences.number_format, Validators.required),
    theme: this.fb.nonNullable.control(this.initialPreferences.theme, Validators.required),
    timezone: this.fb.nonNullable.control(this.initialPreferences.timezone, [Validators.required, Validators.maxLength(50)]),
  });

  constructor() {
    effect(() => {
      const isOpen = this.open();
      if (isOpen) untracked(() => this.loadLocal());
    });
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open()) this.requestClose();
  }


  setLanguage(language: AppLanguage): void {
    this.form.controls.language.setValue(language);
    this.form.controls.language.markAsDirty();
    this.i18n.setLanguage(language);
  }

  setTimezone(timezone: string): void {
    this.form.controls.timezone.setValue(timezone);
    this.form.controls.timezone.markAsDirty();
  }

  setTheme(value: BackendTheme): void {
    const nextTheme: UiTheme = value === 'DARK' ? 'dark' : 'light';
    this.form.controls.theme.setValue(value);
    this.form.controls.theme.markAsDirty();
    this.theme.preview(nextTheme);
    this.errorMessage.set(null);
  }

  save(): void {
    if (this.form.invalid || this.saving() || this.closing()) return;

    this.saving.set(true);
    this.errorMessage.set(null);
    const value = this.form.getRawValue();
    const payload: UserPreferences = {
      language: value.language,
      date_format: value.date_format,
      time_format: value.time_format,
      number_format: value.number_format,
      theme: value.theme,
      timezone: value.timezone,
    };

    this.preferences.save(payload).subscribe({
      next: (saved) => {
        this.saving.set(false);
        this.lastServerPreferences = saved;
        this.committedLanguage = saved.language;
        this.i18n.setLanguage(saved.language);
        this.committedTheme = saved.theme === 'DARK' ? 'dark' : 'light';
        this.theme.set(this.committedTheme);
        this.requestClose();
      },
      error: (error: unknown) => {
        this.saving.set(false);
        this.restoreAfterSaveFailure(this.apiErrors.message(error, 'errors.preferencesSaveFailed'));
      },
    });
  }

  requestClose(): void {
    if (this.closing() || this.saving()) return;

    this.closing.set(true);
    this.preferences.get().subscribe({
      next: (latest) => {
        this.lastServerPreferences = latest;
        this.applyPreferences(latest);
        this.closing.set(false);
        this.close.emit();
      },
      error: () => {
        this.theme.set(this.committedTheme);
        this.i18n.setLanguage(this.committedLanguage);
        this.closing.set(false);
        this.close.emit();
      },
    });
  }

  private loadLocal(): void {
    this.errorMessage.set(null);
    const value = this.preferences.current();
    this.lastServerPreferences = value;
    this.applyPreferences(value);
  }

  private applyPreferences(value: UserPreferences): void {
    const resolvedTheme: UiTheme = value.theme === 'DARK' ? 'dark' : 'light';
    this.i18n.setLanguage(value.language);
    this.committedLanguage = value.language;
    this.committedTheme = resolvedTheme;
    this.theme.set(resolvedTheme);
    this.form.setValue(value, { emitEvent: false });
    this.form.markAsPristine();
  }

  private restoreAfterSaveFailure(message: string): void {
    // Keep the preferences dialog network-silent while it is open. The last
    // known persisted snapshot is enough to undo live language/theme previews;
    // the next GET happens only when the dialog is closed.
    this.applyPreferences(this.lastServerPreferences);
    this.errorMessage.set(message);
  }

  private buildTimezoneOptions(): readonly string[] {
    return Array.from(new Set<string>([this.browserTimezone, 'UTC', ...IANA_TIMEZONES])).sort((a, b) => a.localeCompare(b));
  }
}
