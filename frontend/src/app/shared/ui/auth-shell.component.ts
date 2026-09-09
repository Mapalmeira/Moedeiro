import { ChangeDetectionStrategy, Component } from '@angular/core';
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
      padding: var(--page-shell-padding-start) var(--space-page) var(--page-shell-padding-end);
    }
    .auth-shell__controls {
      position: absolute;
      z-index: var(--layer-page-controls);
      top: var(--page-shell-control-offset);
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
      margin-bottom: var(--page-shell-brand-gap);
      text-align: center;
    }
    .auth-shell__content {
      grid-row: 2;
      width: min(1060px, 100%);
      margin: 0 auto;
    }

    @media (max-width: 860px), (max-height: 760px) {
      .auth-shell { padding-top: var(--page-shell-compact-padding-start); }
      .auth-shell__controls { top: var(--page-shell-compact-control-offset); }
      .auth-shell__body { display: block; margin-block: auto; padding-block: var(--section-gap); }
      .auth-shell__header { margin-bottom: var(--page-shell-brand-gap); }
    }
    @media (max-width: 430px) {
      .auth-shell__controls { gap: var(--space-3); }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthShellComponent {}
