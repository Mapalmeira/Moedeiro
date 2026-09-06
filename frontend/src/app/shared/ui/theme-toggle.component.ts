import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { I18nService } from '../../core/i18n/i18n.service';
import { ThemeService } from '../../core/theme/theme.service';
import { IconComponent } from './icon.component';

@Component({
  selector: 'app-theme-toggle',
  standalone: true,
  imports: [IconComponent],
  template: `
    <button class="theme-toggle ui-select-trigger ui-action-press" type="button" (click)="theme.toggle()"
      [attr.aria-label]="theme.theme() === 'dark' ? i18n.t('theme.useLight') : i18n.t('theme.useDark')"
      [attr.title]="theme.theme() === 'dark' ? i18n.t('theme.useLight') : i18n.t('theme.useDark')">
      <app-icon name="sun" [size]="17" />
      <span class="switch-track" [class.switch-track--dark]="theme.theme() === 'dark'" aria-hidden="true">
        <span></span>
      </span>
      <app-icon name="moon" [size]="17" />
    </button>
  `,
  styles: `
    :host { display: inline-block; }
    .theme-toggle {
      height: var(--control-height);
      min-height: var(--control-height);
      display: inline-flex;
      align-items: center;
      gap: var(--space-2);
      padding: var(--space-2) var(--space-3);
      filter: var(--selection-shadow);
    }
    .switch-track {
      width: 36px;
      height: 20px;
      padding: 2px;
      border: 2px solid var(--line-strong);
      border-radius: 999px;
      background: var(--surface-muted);
      transition: background var(--motion-selection) ease, border-color var(--motion-selection) ease;
    }
    .switch-track > span {
      display: block;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--text);
      transition: transform var(--motion-selection) ease, background var(--motion-selection) ease;
    }
    .switch-track--dark { background: var(--surface); }
    .switch-track--dark > span { transform: translateX(16px); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ThemeToggleComponent {
  readonly theme = inject(ThemeService);
  readonly i18n = inject(I18nService);
}
