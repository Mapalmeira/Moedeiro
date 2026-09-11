import { ChangeDetectionStrategy, Component, effect, inject, input, output, signal, untracked } from '@angular/core';
import { DialogShellComponent } from '../../shared/ui/dialog-shell.component';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ApiErrorService } from '../../core/api/api-error';
import { AppLanguage, I18nService } from '../../core/i18n/i18n.service';
import { BackendTheme, UserPreferences } from '../../core/preferences/preferences.models';
import { PreferencesService } from '../../core/preferences/preferences.service';
import { ThemeService, UiTheme } from '../../core/theme/theme.service';
import { FormMessageComponent } from '../../shared/ui/form-message.component';
import { IconComponent } from '../../shared/ui/icon.component';
import { LanguageSelectorComponent } from '../../shared/ui/language-selector.component';

@Component({
  selector: 'app-preferences-dialog',
  standalone: true,
  imports: [DialogShellComponent, ReactiveFormsModule, FormMessageComponent, IconComponent, LanguageSelectorComponent],
  template: `
    @if (open()) {
      <app-dialog-shell [ariaLabel]="i18n.t('preferences.title')" (dismiss)="requestClose()">
        <header class="dialog__header ui-dialog-header">
          <div class="dialog__title ui-dialog-title">
            <span class="ui-icon-badge ui-icon-badge--dialog ui-icon-badge--green ui-projected-icon"><app-icon name="LucideSlidersHorizontal" size="prominent" /></span>
            <h2>{{ i18n.t('preferences.title') }}</h2>
          </div>
          <button class="icon-button icon-button--control ui-action-press" type="button" (click)="requestClose()" [disabled]="closing() || saving()"
            [attr.aria-label]="i18n.t('common.close')">
            <app-icon name="LucideX" size="control" />
          </button>
        </header>

        <form [formGroup]="form" (ngSubmit)="save()" novalidate>
          <div class="preference-grid">
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
                  <app-icon name="LucideSun" size="control" /><span>{{ i18n.t('theme.light') }}</span>
                </button>
                <button type="button" class="ui-choice choice-card choice-card--with-icon"
                  [class.ui-choice--selected]="form.controls.theme.value === 'DARK'"
                  (click)="setTheme('DARK')">
                  <app-icon name="LucideMoon" size="control" /><span>{{ i18n.t('theme.dark') }}</span>
                </button>
              </div>
            </section>
          </div>

          @if (errorMessage()) { <app-form-message [text]="errorMessage()!" /> }

          <footer class="dialog__footer ui-surface-actions">
            <button class="ui-button ui-button--green" type="submit" [disabled]="form.invalid || saving() || closing()">
              {{ i18n.t('preferences.save') }}
            </button>
          </footer>
        </form>
      </app-dialog-shell>
    }
  `,
  styles: `
    form { display: grid; gap: 0; padding: 0 var(--space-5) var(--space-5); }
    .preference-grid {
      min-height: calc(var(--control-height) + (2 * var(--menu-item-height)) + (4 * var(--section-gap)));
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      align-items: start;
      gap: var(--section-gap);
      padding: var(--section-gap) 0;
    }
    .preference-field { min-width: 0; display: grid; gap: var(--field-gap); padding: var(--section-gap) 0; }
    .preference-grid .preference-field { padding: 0; border: 0; }
    .preference-label { font-size: var(--control-font-size); font-weight: 780; letter-spacing: -.005em; }
    .choice-grid { display: grid; gap: var(--space-2); }
    .choice-grid--2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .choice-card--with-icon { justify-content: flex-start; padding-left: var(--form-gap); }
    .dialog__footer .ui-button { min-width: var(--action-button-min-width); }
    @media (max-width: 650px) { .preference-grid { grid-template-columns: 1fr; } }
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
  private readonly theme = inject(ThemeService);
  private readonly apiErrors = inject(ApiErrorService);
  readonly i18n = inject(I18nService);

  readonly open = input(false);
  readonly close = output<void>();
  readonly saving = signal(false);
  readonly closing = signal(false);
  readonly errorMessage = signal<string | null>(null);

  private readonly initialPreferences = this.preferences.current();
  private lastServerPreferences: UserPreferences = this.initialPreferences;
  private committedTheme: UiTheme = this.theme.theme();
  private committedLanguage: AppLanguage = this.i18n.language();

  readonly form = this.fb.group({
    language: this.fb.nonNullable.control(this.initialPreferences.language, Validators.required),
    theme: this.fb.nonNullable.control(this.initialPreferences.theme, Validators.required),
  });

  constructor() {
    effect(() => {
      const isOpen = this.open();
      if (isOpen) untracked(() => this.loadLocal());
    });
  }

  setLanguage(language: AppLanguage): void {
    this.form.controls.language.setValue(language);
    this.form.controls.language.markAsDirty();
    this.i18n.setLanguage(language);
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
      theme: value.theme,
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
    this.applyPreferences(this.lastServerPreferences);
    this.errorMessage.set(message);
  }

}
