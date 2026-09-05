import { ChangeDetectionStrategy, Component, ElementRef, HostListener, inject, input, output, signal } from '@angular/core';
import { AppLanguage, I18nService } from '../../core/i18n/i18n.service';
import { IconComponent } from './icon.component';
import { TwemojiFlagComponent } from './twemoji-flag.component';

@Component({
  selector: 'app-language-selector',
  standalone: true,
  imports: [IconComponent, TwemojiFlagComponent],
  host: { '[class.language-selector--field]': 'appearance() === "field"' },
  template: `
    <div class="language-selector">
      <button class="language-selector__trigger" type="button" (click)="open.set(!open())"
        [attr.aria-label]="i18n.t('common.language')" [attr.aria-expanded]="open()">
        <span class="language-selector__language-icon" aria-hidden="true">
          <app-icon name="languages" [size]="18" />
        </span>
        <span class="language-selector__name">{{ languageName(selectedLanguage()) }}</span>
        <app-icon class="language-selector__chevron" name="chevron-down" [size]="16" />
      </button>

      @if (open()) {
        <div class="language-selector__menu" role="menu">
          <button type="button" role="menuitem" [class.language-selector__option--selected]="selectedLanguage() === 'pt-BR'"
            (click)="select('pt-BR')">
            <span class="language-selector__option-main">
              <app-twemoji-flag country="br" />
              <span class="language-selector__option-text">{{ i18n.t('language.pt') }}</span>
            </span>
            @if (selectedLanguage() === 'pt-BR') { <app-icon name="check" [size]="16" /> }
          </button>
          <button type="button" role="menuitem" [class.language-selector__option--selected]="selectedLanguage() === 'en'"
            (click)="select('en')">
            <span class="language-selector__option-main">
              <app-twemoji-flag country="us" />
              <span class="language-selector__option-text">{{ i18n.t('language.en') }}</span>
            </span>
            @if (selectedLanguage() === 'en') { <app-icon name="check" [size]="16" /> }
          </button>
        </div>
      }
    </div>
  `,
  styles: `
    :host { display: inline-block; }
    :host.language-selector--field { display: block; width: 100%; }
    .language-selector { position: relative; }
    .language-selector__trigger {
      min-width: 158px;
      min-height: 44px;
      display: grid;
      grid-template-columns: 28px minmax(0, 1fr) 16px;
      align-items: center;
      gap: var(--space-2);
      padding: var(--space-2) var(--space-3);
      border: 2px solid var(--line-strong);
      border-radius: 6px;
      background: var(--surface);
      color: var(--text);
      box-shadow: 3px 3px 0 var(--shadow-color);
      text-align: left;
      font-size: .88rem;
      font-weight: 720;
      line-height: 1.4;
      transition: transform var(--motion-press) ease, box-shadow var(--motion-press) ease, background var(--motion-press) ease;
    }
    :host.language-selector--field .language-selector__trigger {
      width: 100%;
      min-height: 46px;
      min-width: 0;
      padding: var(--space-2) var(--space-3);
      box-shadow: none;
      border-color: var(--line);
      font-size: .9rem;
    }
    .language-selector__trigger:hover { background: var(--surface-muted); }
    .language-selector__trigger:active {
      transform: translate(var(--press-offset), var(--press-offset));
      box-shadow: 1px 1px 0 var(--shadow-color);
    }
    :host.language-selector--field .language-selector__trigger:active { box-shadow: none; }
    .language-selector__language-icon {
      width: 28px;
      height: 28px;
      display: inline-grid;
      place-items: center;
      border: 1px solid var(--line);
      border-radius: 5px;
      background: var(--surface-muted);
      color: var(--text);
    }
    :host.language-selector--field .language-selector__language-icon {
      border-color: transparent;
      background: transparent;
      width: 24px;
      height: 24px;
    }
    .language-selector__name {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      line-height: 1.45;
      padding-block: 1px 2px;
    }
    .language-selector__chevron { transition: transform 130ms ease; }
    .language-selector__trigger[aria-expanded='true'] .language-selector__chevron { transform: rotate(180deg); }
    .language-selector__menu {
      position: absolute;
      z-index: 90;
      top: calc(100% + var(--space-2));
      right: 0;
      width: max(190px, 100%);
      padding: var(--space-1);
      border: 2px solid var(--line-strong);
      border-radius: 7px;
      background: var(--surface);
      box-shadow: 4px 4px 0 var(--shadow-color);
    }
    :host.language-selector--field .language-selector__menu { left: 0; right: auto; width: 100%; }
    .language-selector__menu button {
      width: 100%;
      min-height: 44px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 18px;
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-2) var(--space-3);
      border: 0;
      border-radius: 4px;
      background: transparent;
      color: var(--text);
      text-align: left;
      font-size: .9rem;
      font-weight: 650;
      line-height: 1.25;
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
    .language-selector__menu button:hover { background: var(--surface-muted); }
    .language-selector__option--selected { background: var(--green-soft) !important; }
    @media (max-width: 520px) {
      .language-selector__trigger { min-width: 144px; }
      .language-selector__menu { width: 184px; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LanguageSelectorComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  readonly i18n = inject(I18nService);
  readonly appearance = input<'compact' | 'field'>('compact');
  readonly value = input<AppLanguage | undefined>(undefined);
  readonly valueChange = output<AppLanguage>();
  readonly open = signal(false);

  @HostListener('document:mousedown', ['$event'])
  closeWhenClickingOutside(event: MouseEvent): void {
    if (!this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }

  @HostListener('document:keydown.escape')
  closeOnEscape(): void {
    this.open.set(false);
  }

  selectedLanguage(): AppLanguage {
    return this.value() ?? this.i18n.language();
  }

  select(language: AppLanguage): void {
    if (this.value() === undefined) this.i18n.setLanguage(language);
    this.valueChange.emit(language);
    this.open.set(false);
  }

  languageName(language: AppLanguage): string {
    return language === 'pt-BR' ? this.i18n.t('language.pt') : this.i18n.t('language.en');
  }
}
