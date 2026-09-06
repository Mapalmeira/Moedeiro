import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { I18nService } from '../../core/i18n/i18n.service';
import { PreferencesService } from '../../core/preferences/preferences.service';
import { ThemeService } from '../../core/theme/theme.service';
import { PreferencesDialogComponent } from '../../features/preferences/preferences-dialog.component';
import { SecurityDialogComponent } from '../../features/security/security-dialog.component';
import { BrandLogoComponent } from '../../shared/brand/brand-logo.component';
import { AccountMenuComponent } from '../../shared/ui/account-menu.component';
import { FormMessageComponent } from '../../shared/ui/form-message.component';
import { AuthenticatedShellService } from './authenticated-shell.service';

@Component({
  selector: 'app-authenticated-layout',
  standalone: true,
  imports: [RouterOutlet, BrandLogoComponent, AccountMenuComponent, FormMessageComponent, PreferencesDialogComponent, SecurityDialogComponent],
  template: `
    <main class="app-page" [class.app-page--ledger]="isLedgerRoute()">
      @if (!isLedgerRoute()) {
        <header class="top-area">
          <div class="top-area__brand">
            <app-brand-logo />
          </div>

          <div class="account-wrap">
            <app-account-menu
              [userName]="shell.currentUserName()"
              [loggingOut]="shell.loggingOut()"
              [fullWidth]="true"
              (preferences)="shell.openPreferences()"
              (security)="shell.openSecurity()"
              (logout)="shell.logout()" />
          </div>
        </header>
      }

      <section class="content-area" [class.content-area--ledger]="isLedgerRoute()"><router-outlet /></section>

      @if (shell.logoutError()) { <div class="floating-message"><app-form-message [text]="shell.logoutError()!" /></div> }
      <app-preferences-dialog [open]="shell.preferencesOpen()" (close)="shell.closePreferences()" />
      <app-security-dialog [open]="shell.securityOpen()" (close)="shell.closeSecurity()" />
    </main>
  `,
  styles: `
    .app-page {
      position: relative;
      min-height: 100dvh;
      display: grid;
      grid-template-rows: minmax(0, 1fr) auto minmax(0, 1fr);
      padding: var(--space-5) var(--space-page);
    }
    .app-page--ledger { display: block; padding: 0; }
    .top-area { grid-row: 1; align-self: end; display: grid; place-items: center; margin-bottom: var(--space-8); }
    .top-area__brand { display: grid; justify-items: center; text-align: center; }
    .account-wrap { position: absolute; top: var(--space-7); right: var(--space-page); z-index: var(--layer-page-controls); width: min(230px, calc(100vw - (2 * var(--space-page)))); }
    .content-area { grid-row: 2; width: min(1180px, 100%); min-height: 0; margin: 0 auto; }
    .content-area--ledger { width: 100%; min-height: 100dvh; margin: 0; }
    .floating-message { position: fixed; right: var(--space-5); bottom: var(--space-5); width: min(430px, calc(100vw - (2 * var(--space-5)))); z-index: var(--layer-toast); }
    @media (max-width: 700px) {
      .app-page:not(.app-page--ledger) {
        grid-template-rows: minmax(0, 1fr) auto minmax(0, 1fr);
        padding: 76px var(--space-page) var(--space-5);
      }
      .top-area { align-self: end; margin-bottom: var(--space-6); }
      .account-wrap { top: var(--space-4); }
      .content-area:not(.content-area--ledger) { align-self: center; margin: 0 auto; }
    }
    @media (max-height: 620px) {
      .app-page:not(.app-page--ledger) { display: block; padding-top: 88px; }
      .top-area { margin-bottom: var(--space-6); }
      .content-area:not(.content-area--ledger) { margin: 0 auto; }
    }
    @media (max-width: 520px) {
      .account-wrap { width: min(205px, calc(100vw - (2 * var(--space-page)))); }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthenticatedLayoutComponent {
  private readonly preferences = inject(PreferencesService);
  private readonly theme = inject(ThemeService);
  private readonly router = inject(Router);
  readonly shell = inject(AuthenticatedShellService);
  readonly i18n = inject(I18nService);

  private readonly navigationEnd = toSignal(
    this.router.events.pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd)),
    { initialValue: null },
  );

  readonly isLedgerRoute = computed(() => {
    this.navigationEnd();
    return this.router.url.startsWith('/ledgers/');
  });

  constructor() {
    this.preferences.getOrInitialize().subscribe({
      next: (value) => {
        this.theme.applyBackendPreference(value.theme);
        this.i18n.setLanguage(value.language);
      },
    });

  }
}
