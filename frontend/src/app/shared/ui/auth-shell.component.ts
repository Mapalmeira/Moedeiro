import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { I18nService } from '../../core/i18n/i18n.service';
import { BrandLogoComponent } from '../brand/brand-logo.component';
import { LanguageSelectorComponent } from './language-selector.component';
import { ThemeToggleComponent } from './theme-toggle.component';

@Component({
  selector: 'app-auth-shell',
  standalone: true,
  imports: [BrandLogoComponent, LanguageSelectorComponent, ThemeToggleComponent],
  template: `
    <main class="auth-shell">
      <div class="auth-shell__controls">
        <app-theme-toggle />
        <app-language-selector />
      </div>

      <div class="auth-shell__body">
        <header class="auth-shell__header">
          <app-brand-logo />
          <p>{{ i18n.t('auth.subtitle') }}</p>
        </header>
        <div class="auth-shell__content"><ng-content /></div>
      </div>
    </main>
  `,
  styles: `
    .auth-shell {
      position: relative;
      min-height: 100dvh;
      display: flex;
      flex-direction: column;
      padding: clamp(30px, 4.5vw, 56px) var(--space-page) 48px;
    }
    .auth-shell__controls {
      position: absolute;
      z-index: 10;
      top: 26px;
      left: var(--space-page);
      right: var(--space-page);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: var(--form-gap);
      pointer-events: none;
    }
    .auth-shell__controls > * { pointer-events: auto; }

    /* The cards own the vertical center. The branding occupies the flexible row
       above them, so its visual weight no longer pushes the cards downward. */
    .auth-shell__body {
      width: 100%;
      flex: 1 1 auto;
      display: grid;
      grid-template-rows: minmax(0, 1fr) auto minmax(0, 1fr);
      min-height: 0;
    }
    .auth-shell__header {
      grid-row: 1;
      align-self: end;
      display: grid;
      justify-items: center;
      gap: var(--space-2);
      margin-bottom: var(--space-8);
      text-align: center;
    }
    .auth-shell__header p {
      margin: 0;
      color: var(--text-muted);
      font-size: clamp(1rem, 1.7vw, 1.2rem);
    }
    .auth-shell__content {
      grid-row: 2;
      width: min(1060px, 100%);
      margin: 0 auto;
    }

    @media (max-width: 860px), (max-height: 760px) {
      .auth-shell { padding-top: 92px; }
      .auth-shell__controls { top: 20px; }
      .auth-shell__body { display: block; margin-block: auto; padding-block: var(--section-gap); }
      .auth-shell__header { margin-bottom: var(--space-8); }
    }
    @media (max-width: 430px) {
      .auth-shell__controls { gap: var(--space-3); }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthShellComponent {
  readonly i18n = inject(I18nService);
}
