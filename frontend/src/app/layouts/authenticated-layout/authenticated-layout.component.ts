import { ChangeDetectionStrategy, Component, HostListener, inject, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';
import { I18nService } from '../../core/i18n/i18n.service';
import { PreferencesService } from '../../core/preferences/preferences.service';
import { ThemeService } from '../../core/theme/theme.service';
import { PreferencesDialogComponent } from '../../features/preferences/preferences-dialog.component';
import { SecurityDialogComponent } from '../../features/security/security-dialog.component';
import { BrandLogoComponent } from '../../shared/brand/brand-logo.component';
import { FormMessageComponent } from '../../shared/ui/form-message.component';
import { IconComponent } from '../../shared/ui/icon.component';

@Component({
  selector: 'app-authenticated-layout',
  standalone: true,
  imports: [RouterOutlet, BrandLogoComponent, IconComponent, FormMessageComponent, PreferencesDialogComponent, SecurityDialogComponent],
  template: `
    <main class="app-page">
      <header class="top-area">
        <div class="top-area__brand">
          <app-brand-logo />
        </div>

        <div class="settings-wrap">
          <button class="settings-button" type="button" (click)="settingsOpen.set(!settingsOpen())"
            [attr.aria-label]="i18n.t('shell.settings')" [attr.aria-expanded]="settingsOpen()">
            <app-icon name="gear" [size]="21" />
          </button>
          @if (settingsOpen()) {
            <div class="settings-menu" role="menu">
              <button type="button" role="menuitem" (click)="openPreferences()">
                <span class="settings-menu__icon settings-menu__icon--green"><app-icon name="sliders" [size]="17" /></span>
                <span>{{ i18n.t('shell.preferences') }}</span>
              </button>
              <button type="button" role="menuitem" (click)="openSecurity()">
                <span class="settings-menu__icon settings-menu__icon--blue"><app-icon name="shield" [size]="17" /></span>
                <span>{{ i18n.t('shell.security') }}</span>
              </button>
              <button class="settings-menu__logout" type="button" role="menuitem" (click)="logout()" [disabled]="loggingOut()">
                <span class="settings-menu__icon settings-menu__icon--yellow"><app-icon name="logout" [size]="17" /></span>
                <span>{{ loggingOut() ? i18n.t('shell.loggingOut') : i18n.t('shell.logout') }}</span>
              </button>
            </div>
          }
        </div>
      </header>

      <section class="content-area"><router-outlet /></section>

      @if (accountCreated()) { <div class="floating-message"><app-form-message kind="success" [text]="i18n.t('auth.register.success')" /></div> }
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
    .top-area {
      grid-row: 1;
      align-self: end;
      display: grid;
      place-items: center;
      margin-bottom: var(--space-8);
    }
    .top-area__brand { display: grid; justify-items: center; text-align: center; }
    .settings-wrap { position: absolute; top: 28px; right: var(--space-page); z-index: 10; }
    .settings-button { display: grid; place-items: center; width: 42px; height: 42px; padding: 0; border: 2px solid var(--line-strong); border-radius: 6px; background: var(--surface); color: var(--text); box-shadow: var(--compact-button-shadow); transition: transform var(--motion-press) ease, box-shadow var(--motion-press) ease, background var(--motion-press) ease; }
    .settings-button:hover { background: var(--surface-muted); }
    .settings-button:active { transform: translate(var(--press-offset), var(--press-offset)); box-shadow: var(--compact-button-shadow-pressed); }
    .settings-menu { position: absolute; top: 52px; right: 0; width: 216px; padding: 8px; border: 2px solid var(--line-strong); border-radius: 8px; background: var(--surface); box-shadow: 5px 5px 0 var(--shadow-color); }
    .settings-menu button { width: 100%; min-height: 46px; display: grid; grid-template-columns: 32px minmax(0, 1fr); align-items: center; gap: 10px; padding: 6px 8px; border: 0; border-radius: 5px; background: transparent; color: var(--text); text-align: left; font-size: .98rem; font-weight: 720; line-height: 1.2; }
    .settings-menu button:hover { background: var(--surface-muted); }
    .settings-menu button + button { margin-top: 3px; }
    .settings-menu__icon { width: 30px; height: 30px; display: grid; place-items: center; border: 1.5px solid var(--line-strong); border-radius: 5px; box-shadow: 1px 1px 0 var(--shadow-color); }
    .settings-menu__icon--green { background: var(--green); color: #07130c; border-color: color-mix(in srgb, var(--green-strong) 78%, var(--line-strong)); }
    .settings-menu__icon--blue { background: var(--blue); color: #07111f; border-color: color-mix(in srgb, var(--blue-strong) 78%, var(--line-strong)); }
    .settings-menu__icon--yellow { background: var(--yellow); color: #171200; border-color: color-mix(in srgb, var(--yellow-strong) 80%, var(--line-strong)); }
    .content-area { grid-row: 2; width: min(1180px, 100%); min-height: 0; margin: 0 auto; }
    .floating-message { position: fixed; right: 20px; bottom: 20px; width: min(430px, calc(100vw - 40px)); z-index: 80; }
    @media (max-width: 700px), (max-height: 760px) {
      .app-page { display: block; padding-top: 84px; }
      .top-area { margin-bottom: var(--space-8); }
      .settings-wrap { top: 20px; }
      .content-area { margin: 0 auto; }
      .settings-menu { top: 49px; width: 188px; padding: 6px; box-shadow: 4px 4px 0 var(--shadow-color); }
      .settings-menu button { min-height: 40px; grid-template-columns: 28px minmax(0, 1fr); gap: 8px; padding: 4px 7px; font-size: .91rem; }
      .settings-menu button + button { margin-top: 2px; }
      .settings-menu__icon { width: 26px; height: 26px; border-radius: 4px; box-shadow: 1px 1px 0 var(--shadow-color); }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthenticatedLayoutComponent {
  private readonly auth = inject(AuthService);
  private readonly preferences = inject(PreferencesService);
  private readonly apiErrors = inject(ApiErrorService);
  private readonly theme = inject(ThemeService);
  readonly i18n = inject(I18nService);

  readonly settingsOpen = signal(false);
  readonly preferencesOpen = signal(false);
  readonly securityOpen = signal(false);
  readonly loggingOut = signal(false);
  readonly logoutError = signal<string | null>(null);
  readonly accountCreated = signal(history.state?.accountCreated === true);

  constructor() {
    this.preferences.getOrInitialize().subscribe({
      next: (value) => {
        this.theme.applyBackendPreference(value.theme);
        this.i18n.setLanguage(value.language);
      },
    });

    if (this.accountCreated()) {
      setTimeout(() => this.accountCreated.set(false), 4500);
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.settingsOpen.set(false);
  }

  openPreferences(): void {
    this.settingsOpen.set(false);
    this.preferencesOpen.set(true);
  }

  openSecurity(): void {
    this.settingsOpen.set(false);
    this.securityOpen.set(true);
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
