import { ChangeDetectionStrategy, Component, inject, input, output, signal } from '@angular/core';
import { DismissiblePopoverDirective } from './dismissible-popover.directive';
import { AppLanguage, I18nService } from '../../core/i18n/i18n.service';
import { IconComponent } from './icon.component';
import { TwemojiFlagComponent } from './twemoji-flag.component';
import { isListboxNavigationKey, nextListboxIndex } from './listbox-navigation';

@Component({
  selector: 'app-language-selector',
  standalone: true,
  imports: [DismissiblePopoverDirective, IconComponent, TwemojiFlagComponent],
  host: { '[class.language-selector--field]': 'appearance() === "field"' },
  template: `
    <div class="language-selector" [appDismissiblePopover]="open()" (dismiss)="closeList()">
      <button class="language-selector__trigger ui-select-trigger ui-trigger-with-icon" type="button" (click)="toggleList()"
        [class.ui-action-press]="appearance() === 'compact'"
        [attr.aria-label]="i18n.t('common.language')" aria-haspopup="listbox" [attr.aria-expanded]="open()" [attr.aria-controls]="listId"
        [attr.aria-activedescendant]="open() ? activeOptionId() : null" (keydown)="handleKeydown($event)">
        <span class="language-selector__language-icon ui-icon-badge" [class.ui-projected-icon]="appearance() === 'compact'" aria-hidden="true">
          @if (appearance() === 'field') {
            <app-twemoji-flag [country]="languageCountry(selectedLanguage())" />
          } @else {
            <app-icon name="LucideLanguages" size="control" />
          }
        </span>
        <span class="language-selector__name">{{ languageName(selectedLanguage()) }}</span>
        <app-icon class="language-selector__chevron ui-select-chevron" name="LucideChevronDown" size="compact" />
      </button>

      @if (open()) {
        <div class="language-selector__menu ui-dropdown-menu ui-projected-surface" role="listbox" [id]="listId">
          <button type="button" role="option" [id]="optionId(0)" tabindex="-1" [attr.aria-selected]="selectedLanguage() === 'pt-BR'" [class.language-selector__option--selected]="selectedLanguage() === 'pt-BR'"
            (click)="select('pt-BR')">
            <span class="language-selector__option-main">
              <app-twemoji-flag country="br" />
              <span class="language-selector__option-text">{{ i18n.t('language.pt') }}</span>
            </span>
            @if (selectedLanguage() === 'pt-BR') { <app-icon name="LucideCheck" size="compact" /> }
          </button>
          <button type="button" role="option" [id]="optionId(1)" tabindex="-1" [attr.aria-selected]="selectedLanguage() === 'en'" [class.language-selector__option--selected]="selectedLanguage() === 'en'"
            (click)="select('en')">
            <span class="language-selector__option-main">
              <app-twemoji-flag country="us" />
              <span class="language-selector__option-text">{{ i18n.t('language.en') }}</span>
            </span>
            @if (selectedLanguage() === 'en') { <app-icon name="LucideCheck" size="compact" /> }
          </button>
        </div>
      }
    </div>
  `,
  styles: `
    :host { display: inline-block; width: 190px; }
    :host.language-selector--field { display: block; width: 100%; }
    .language-selector { position: relative; width: 100%; }
    :host.language-selector--field .language-selector { display: grid; grid-template-columns: minmax(0, 1fr); }
    .language-selector__trigger {
      width: 100%;
      min-width: 0;
      height: var(--sidebar-control-height);
      min-height: var(--sidebar-control-height);
      text-align: left;
    }
    :host.language-selector--field .language-selector__trigger {
      height: var(--control-height);
      min-height: var(--control-height);
      grid-template-columns: var(--inline-icon-size) minmax(0, 1fr) var(--chevron-track-size);
      gap: var(--space-2);
      padding: var(--space-2) var(--space-3);
    }
    .language-selector__language-icon {
      background: var(--blue);
      color: var(--on-blue);
    }
    :host.language-selector--field .language-selector__language-icon {
      --icon-badge-size: var(--inline-icon-size);
      border-color: transparent;
      background: transparent;
      box-shadow: none;
    }
    :host.language-selector--field .language-selector__language-icon app-twemoji-flag { display: grid; width: 100%; height: 100%; }
    .language-selector__name {
      min-width: 0;
      text-align: left;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .language-selector__chevron { justify-self: end; }
    .language-selector__menu {
      position: absolute;
      z-index: var(--layer-dropdown);
      top: calc(100% + var(--space-2));
      left: 0;
      width: 100%;
    }
    .language-selector__menu button {
      width: 100%;
      min-height: var(--menu-item-height);
      display: grid;
      grid-template-columns: minmax(0, 1fr) 18px;
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-2) var(--space-3);
      border: 0;
      background: transparent;
      color: var(--text);
      text-align: left;
      font-size: var(--control-font-size);
      font-weight: 650;
      line-height: var(--control-line-height);
    }
    .language-selector__option-main {
      min-width: 0;
      display: flex;
      align-items: center;
      gap: var(--space-3);
    }
    .language-selector__option-main app-twemoji-flag { flex: 0 0 22px; }
    .language-selector__option-text {
      min-width: 0;
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .language-selector__menu button:not(.language-selector__option--selected):hover { background: var(--surface-muted); }
    .language-selector__option--selected, .language-selector__option--selected:hover { background: var(--green-soft); }
    @media (max-width: 520px) {
      :host:not(.language-selector--field) { width: 176px; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LanguageSelectorComponent {
  private static nextId = 0;
  readonly i18n = inject(I18nService);
  readonly appearance = input<'compact' | 'field'>('compact');
  readonly value = input<AppLanguage | undefined>(undefined);
  readonly valueChange = output<AppLanguage>();
  readonly open = signal(false);
  readonly activeIndex = signal(-1);
  readonly listId = `language-selector-${LanguageSelectorComponent.nextId++}`;
  readonly activeOptionId = () => this.activeIndex() >= 0 ? this.optionId(this.activeIndex()) : null;


  toggleList(): void {
    if (this.open()) {
      this.closeList();
      return;
    }
    this.open.set(true);
    this.activeIndex.set(this.selectedLanguage() === 'pt-BR' ? 0 : 1);
  }

  closeList(): void {
    this.open.set(false);
    this.activeIndex.set(-1);
  }

  handleKeydown(event: KeyboardEvent): void {
    if (isListboxNavigationKey(event.key)) {
      event.preventDefault();
      if (!this.open()) this.toggleList();
      else this.activeIndex.set(nextListboxIndex(this.activeIndex(), 2, event.key));
      return;
    }
    if (this.open() && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      this.select(this.activeIndex() === 1 ? 'en' : 'pt-BR');
    }
  }

  optionId(index: number): string { return `${this.listId}-option-${index}`; }

  selectedLanguage(): AppLanguage {
    return this.value() ?? this.i18n.language();
  }

  select(language: AppLanguage): void {
    if (this.value() === undefined) this.i18n.setLanguage(language);
    this.valueChange.emit(language);
    this.closeList();
  }

  languageName(language: AppLanguage): string {
    return language === 'pt-BR' ? this.i18n.t('language.pt') : this.i18n.t('language.en');
  }

  languageCountry(language: AppLanguage): 'br' | 'us' {
    return language === 'pt-BR' ? 'br' : 'us';
  }
}
