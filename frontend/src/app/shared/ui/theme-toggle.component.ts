import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { I18nService } from '../../core/i18n/i18n.service';
import { ThemeService } from '../../core/theme/theme.service';
import { IconComponent } from './icon.component';

@Component({
  selector: 'app-theme-toggle',
  standalone: true,
  imports: [IconComponent],
  template: `
    <button class="theme-toggle" type="button" (click)="theme.toggle()"
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
    .theme-toggle {
      min-height: 44px;
      display: inline-flex;
      align-items: center;
      gap: var(--space-2);
      padding: var(--space-2) var(--space-3);
      border: 2px solid var(--line-strong);
      border-radius: 6px;
      background: var(--surface);
      color: var(--text);
      box-shadow: 3px 3px 0 var(--shadow-color);
      transition: transform var(--motion-press) ease, box-shadow var(--motion-press) ease, background var(--motion-press) ease;
    }
    .theme-toggle:hover { background: var(--surface-muted); }
    .theme-toggle:active { transform: translate(var(--press-offset), var(--press-offset)); box-shadow: 1px 1px 0 var(--shadow-color); }
    .switch-track {
      width: 36px;
      height: 20px;
      padding: 2px;
      border: 2px solid var(--line-strong);
      border-radius: 999px;
      background: var(--surface-muted);
      transition: background .16s ease, border-color .16s ease;
    }
    .switch-track > span {
      display: block;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--text);
      transition: transform .16s ease, background .16s ease;
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
