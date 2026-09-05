import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter, finalize } from 'rxjs';
import { ApiErrorService } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';
import { I18nService } from '../../core/i18n/i18n.service';
import { PreferencesService } from '../../core/preferences/preferences.service';
import { ThemeService } from '../../core/theme/theme.service';
import { PreferencesDialogComponent } from '../../features/preferences/preferences-dialog.component';
import { SecurityDialogComponent } from '../../features/security/security-dialog.component';
import { BrandLogoComponent } from '../../shared/brand/brand-logo.component';
import { AccountMenuComponent } from '../../shared/ui/account-menu.component';
import { FormMessageComponent } from '../../shared/ui/form-message.component';

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
              [userName]="currentUserName()"
              [loggingOut]="loggingOut()"
              [fullWidth]="true"
              (preferences)="preferencesOpen.set(true)"
              (security)="securityOpen.set(true)"
              (logout)="logout()" />
          </div>
        </header>
      }

      <section class="content-area" [class.content-area--ledger]="isLedgerRoute()"><router-outlet /></section>

      @if (logoutError()) { <div class="floating-message"><app-form-message [text]="logoutError()!" /></div> }
      <app-preferences-dialog [open]="preferencesOpen()" (close)="preferencesOpen.set(false)" />
      <app-security-dialog [open]="securityOpen()" (close)="securityOpen.set(false)" />
    </main>
  `,
  styles: `
    .app-page {
      position: relative;
      min-height: 100dvh;
      display: grid;
      grid-template-rows: minmax(0, 1fr) auto minmax(0, 1fr);
      padding: 24px var(--space-page) 60px;
    }
    .app-page--ledger { display: block; padding: 0; }
    .top-area { grid-row: 1; align-self: end; display: grid; place-items: center; margin-bottom: var(--space-8); }
    .top-area__brand { display: grid; justify-items: center; text-align: center; }
    .account-wrap { position: absolute; top: 28px; right: var(--space-page); z-index: 10; width: min(230px, calc(100vw - (2 * var(--space-page)))); }
    .content-area { grid-row: 2; width: min(1180px, 100%); min-height: 0; margin: 0 auto; }
    .content-area--ledger { width: 100%; min-height: 100dvh; margin: 0; }
    .floating-message { position: fixed; right: 20px; bottom: 20px; width: min(430px, calc(100vw - 40px)); z-index: 80; }
    @media (max-width: 700px) {
      .app-page:not(.app-page--ledger) {
        grid-template-rows: minmax(0, 1fr) auto minmax(0, 1fr);
        padding: 76px var(--space-page) 32px;
      }
      .top-area { align-self: end; margin-bottom: var(--space-6); }
      .account-wrap { top: 16px; }
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
  private readonly auth = inject(AuthService);
  private readonly preferences = inject(PreferencesService);
  private readonly apiErrors = inject(ApiErrorService);
  private readonly theme = inject(ThemeService);
  private readonly router = inject(Router);
  readonly i18n = inject(I18nService);

  readonly preferencesOpen = signal(false);
  readonly securityOpen = signal(false);
  readonly loggingOut = signal(false);
  readonly logoutError = signal<string | null>(null);
  readonly isLedgerRoute = signal(this.router.url.startsWith('/ledgers/'));
  readonly currentUserName = this.auth.currentUserName.asReadonly();

  constructor() {
    this.preferences.getOrInitialize().subscribe({
      next: (value) => {
        this.theme.applyBackendPreference(value.theme);
        this.i18n.setLanguage(value.language);
      },
    });

    this.router.events.pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd)).subscribe((event) => {
      this.isLedgerRoute.set(event.urlAfterRedirects.startsWith('/ledgers/'));
    });

  }

  logout(): void {
    if (this.loggingOut()) return;
    this.loggingOut.set(true);
    this.logoutError.set(null);
    this.auth.logout().pipe(finalize(() => this.loggingOut.set(false))).subscribe({
      next: () => void this.auth.finishLogout(),
      error: (error) => this.logoutError.set(this.apiErrors.message(error, 'errors.logoutFailed')),
    });
  }
}
