import { ChangeDetectionStrategy, Component, HostListener, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';
import { I18nService } from '../../core/i18n/i18n.service';
import { LedgerService } from '../../core/ledgers/ledger.service';
import { LedgerEditorDialogComponent } from './ledger-editor-dialog.component';
import { BrandLogoComponent } from '../../shared/brand/brand-logo.component';
import { PreferencesDialogComponent } from '../preferences/preferences-dialog.component';
import { SecurityDialogComponent } from '../security/security-dialog.component';
import { bestContrastingForeground } from '../../shared/ledger/ledger-appearance';
import { LedgerIconComponent } from '../../shared/ledger/ledger-icon.component';
import { AccountMenuComponent } from '../../shared/ui/account-menu.component';
import { FormMessageComponent } from '../../shared/ui/form-message.component';
import { IconComponent, IconName } from '../../shared/ui/icon.component';

interface LedgerSectionItem {
  key: LedgerSectionKey;
  labelKey: 'ledgerShell.home' | 'ledgerShell.activity' | 'ledgerShell.budgets' | 'ledgerShell.analytics' | 'ledgerShell.accounts' | 'ledgerShell.categories' | 'ledgerShell.currencies';
  icon: IconName;
  tone: 'green' | 'yellow' | 'blue' | 'neutral';
}

type LedgerSectionKey = 'home' | 'activity' | 'budgets' | 'analytics' | 'accounts' | 'categories' | 'currencies';

const MOBILE_NAV_ACTION_DELAY_MS = 160;

const LEDGER_SECTION_ITEMS: LedgerSectionItem[] = [
  { key: 'home', labelKey: 'ledgerShell.home', icon: 'house', tone: 'green' },
  { key: 'activity', labelKey: 'ledgerShell.activity', icon: 'arrow-left-right', tone: 'neutral' },
  { key: 'budgets', labelKey: 'ledgerShell.budgets', icon: 'wallet', tone: 'yellow' },
  { key: 'analytics', labelKey: 'ledgerShell.analytics', icon: 'chart', tone: 'blue' },
  { key: 'accounts', labelKey: 'ledgerShell.accounts', icon: 'building', tone: 'green' },
  { key: 'categories', labelKey: 'ledgerShell.categories', icon: 'layers', tone: 'neutral' },
  { key: 'currencies', labelKey: 'ledgerShell.currencies', icon: 'coins', tone: 'yellow' },
];

@Component({
  selector: 'app-ledger-page',
  standalone: true,
  imports: [IconComponent, LedgerIconComponent, BrandLogoComponent, AccountMenuComponent, FormMessageComponent, LedgerEditorDialogComponent, PreferencesDialogComponent, SecurityDialogComponent],
  template: `
    <div class="ledger-shell">
      @if (isMobile() && mobileSidebarOpen()) {
        <button class="mobile-overlay" type="button" (click)="closeMobileNavigation()" [attr.aria-label]="i18n.t('ledgerShell.collapse')"></button>
      }

      <aside class="ledger-sidebar" [class.ledger-sidebar--mobile-open]="mobileSidebarOpen()">
        <div class="ledger-sidebar__inner">
          <header class="ledger-sidebar__brand-row">
            <app-brand-logo variant="sidebar" />
          </header>

          <nav class="ledger-nav" [attr.aria-label]="i18n.t('ledgerShell.navigation')">
            @for (item of navItems; track item.key) {
              <button class="ledger-nav__item" type="button" [class.ledger-nav__item--active]="selectedSection() === item.key"
                (click)="openSection(item.key)">
                <span class="ledger-nav__icon"
                  [class.ledger-nav__icon--green]="item.tone === 'green'"
                  [class.ledger-nav__icon--yellow]="item.tone === 'yellow'"
                  [class.ledger-nav__icon--blue]="item.tone === 'blue'"
                  [class.ledger-nav__icon--neutral]="item.tone === 'neutral'">
                  <app-icon [name]="item.icon" [size]="18" />
                </span>
                <span class="ledger-nav__label">{{ i18n.t(item.labelKey) }}</span>
              </button>
            }
          </nav>

          <div class="ledger-sidebar__spacer"></div>

          <div class="ledger-sidebar__footer">
            @if (currentLedger(); as ledger) {
              <div class="ledger-switcher" (click)="$event.stopPropagation()">
                <button class="ledger-switcher__trigger ui-select-trigger ui-action-press" type="button"
                  (click)="toggleLedgerMenu($event)" [attr.aria-expanded]="ledgerMenuOpen()" [attr.title]="ledger.name">
                  <span class="ledger-switcher__icon" [style.background]="ledger.color_code" [style.color]="ledgerForeground()">
                    <app-ledger-icon [icon]="ledger.icon" [size]="20" />
                  </span>
                  <strong class="ledger-switcher__name">{{ ledger.name }}</strong>
                  <app-icon class="ledger-switcher__chevron ui-select-chevron" name="chevron-down" [size]="16" />
                </button>

                @if (ledgerMenuOpen()) {
                  <div class="ledger-switcher__dropdown" role="menu">
                    <button type="button" role="menuitem" (click)="editCurrentLedger()">
                      <span class="ledger-switcher__menu-icon ledger-switcher__menu-icon--edit"><app-icon name="pencil" [size]="17" /></span>
                      <span>{{ i18n.t('ledgers.edit') }}</span>
                    </button>
                    <button type="button" role="menuitem" (click)="leaveLedger()">
                      <span class="ledger-switcher__menu-icon ledger-switcher__menu-icon--leave"><app-icon name="logout" [size]="17" /></span>
                      <span>{{ i18n.t('ledgerShell.leave') }}</span>
                    </button>
                  </div>
                }
              </div>
            }

            <app-account-menu
              [userName]="currentUserName()"
              [loggingOut]="loggingOut()"
              placement="up"
              [fullWidth]="true"
              (preferences)="preferencesOpen.set(true)"
              (security)="securityOpen.set(true)"
              (logout)="logout()" />
          </div>
        </div>
      </aside>

      <section class="ledger-main">
        <header class="ledger-main__header">
          <button class="mobile-nav-button ui-action-press" type="button" (click)="openMobileNavigation()"
            [attr.aria-label]="i18n.t('ledgerShell.navigation')">
            <app-icon name="panel-open" [size]="20" />
          </button>

          <div class="ledger-main__headline">
            <span class="ledger-main__token"
              [class.ledger-main__token--green]="activeNavItem().tone === 'green'"
              [class.ledger-main__token--yellow]="activeNavItem().tone === 'yellow'"
              [class.ledger-main__token--blue]="activeNavItem().tone === 'blue'"
              [class.ledger-main__token--neutral]="activeNavItem().tone === 'neutral'">
              <app-icon [name]="activeNavItem().icon" [size]="20" />
            </span>
            <div class="ledger-main__title-wrap">
              <h1>{{ sectionLabel() }}</h1>
            </div>
          </div>
        </header>

        @if (loadError()) {
          <div class="placeholder-card placeholder-card--error">
            <app-form-message [text]="loadError()!" />
            <div class="placeholder-card__actions">
              <button class="ui-button ui-button--green" type="button" (click)="goHome()">{{ i18n.t('ledgerShell.backToLedgers') }}</button>
            </div>
          </div>
        } @else if (loading() && !currentLedger()) {
          <div class="placeholder-card placeholder-card--loading">
            <div class="spinner" aria-hidden="true"></div>
            <p>{{ i18n.t('ledgers.entering') }}</p>
          </div>
        } @else {
          <div class="ledger-section-content" aria-live="polite"></div>
        }
      </section>

      @if (logoutError()) { <div class="floating-message"><app-form-message [text]="logoutError()!" /></div> }
      <app-preferences-dialog [open]="preferencesOpen()" (close)="preferencesOpen.set(false)" />
      <app-security-dialog [open]="securityOpen()" (close)="securityOpen.set(false)" />
      <app-ledger-editor-dialog [open]="ledgerEditorOpen()" [ledger]="currentLedger()"
        (close)="ledgerEditorOpen.set(false)" (saved)="ledgerEditorOpen.set(false)" />
    </div>
  `,
  styles: `
    :host { display: block; min-height: 100dvh; }
    .ledger-shell {
      --sidebar-width: 268px;
      min-height: 100dvh;
      display: grid;
      grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
      background: var(--page);
      color: var(--text);
    }
    .ledger-sidebar {
      position: sticky;
      top: 0;
      min-height: 100dvh;
      border-right: 2px solid var(--line);
      background: var(--surface);
      transition: width .18s ease, transform .18s ease;
      overflow: hidden;
    }
    .ledger-sidebar__inner { min-height: 100dvh; display: flex; flex-direction: column; gap: var(--space-6); padding: var(--space-5) var(--space-4); }
    .ledger-sidebar__brand-row { min-height: 50px; width: 100%; }
    .ledger-sidebar__brand-row app-brand-logo { width: 100%; height: 50px; }
    .mobile-nav-button {
      display: grid; place-items: center; width: 40px; height: 40px; padding: 0; border: 2px solid var(--line-strong);
      border-radius: 6px; background: var(--surface); color: var(--text);
    }
    .mobile-nav-button:hover { background: var(--surface-muted); }
    .ledger-nav { display: grid; gap: var(--space-2); }
    .ledger-nav__item {
      min-height: 52px; display: grid; grid-template-columns: 36px minmax(0, 1fr); align-items: center; gap: var(--space-3);
      padding: var(--space-2) var(--space-3); border: 2px solid transparent; border-radius: 6px; background: transparent; color: var(--text); box-shadow: var(--selection-shadow-transparent);
      text-align: left; font-size: var(--control-font-size); font-weight: var(--control-font-weight); line-height: var(--control-line-height); transition: box-shadow var(--motion-selection) ease, background var(--motion-selection) ease, border-color var(--motion-selection) ease;
    }
    .ledger-nav__item:not(.ledger-nav__item--active):hover { background: var(--surface-muted); }
    .ledger-nav__item--active { border-color: var(--line-strong); background: var(--green-soft); color: var(--text); box-shadow: var(--selection-shadow); }
    .ledger-nav__icon { width: var(--control-icon-size); height: var(--control-icon-size); display: grid; place-items: center; border: 2px solid var(--line-strong); border-radius: 5px; box-shadow: var(--icon-shadow); }
    .ledger-nav__icon--green { background: var(--green); color: #07130c; }
    .ledger-nav__icon--yellow { background: var(--yellow); color: #171200; }
    .ledger-nav__icon--blue { background: var(--blue); color: #ffffff; }
    .ledger-nav__icon--neutral { background: var(--surface-muted); color: var(--text); }
    .ledger-nav__label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .ledger-sidebar__spacer { flex: 1 1 auto; }
    .ledger-sidebar__footer { display: grid; gap: var(--space-3); }
    .ledger-switcher { position: relative; min-width: 0; }
    .ledger-switcher__trigger {
      width: 100%; min-width: 0; min-height: var(--sidebar-control-height); display: grid;
      grid-template-columns: var(--control-icon-size) minmax(0, 1fr) 16px; align-items: center; gap: var(--space-3);
      padding: var(--space-2) var(--space-3); text-align: left;
    }
    .ledger-switcher__icon {
      width: var(--control-icon-size); height: var(--control-icon-size); display: grid; place-items: center; overflow: hidden;
      border: 2px solid var(--line-strong); border-radius: 5px; box-shadow: var(--icon-shadow);
    }
    .ledger-switcher__name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: inherit; }
    .ledger-switcher__chevron { justify-self: end; }
    .ledger-switcher__dropdown {
      position: absolute; z-index: 90; left: 0; right: 0; bottom: calc(100% + var(--space-2));
      padding: var(--space-2); border: 2px solid var(--line-strong); border-radius: 8px;
      background: var(--surface); box-shadow: var(--compact-button-shadow);
    }
    .ledger-switcher__dropdown button {
      width: 100%; min-height: var(--control-height); display: grid; grid-template-columns: var(--control-icon-size) minmax(0, 1fr);
      align-items: center; gap: var(--space-3); padding: var(--space-2); border: 0; border-radius: 5px;
      background: transparent; color: var(--text); text-align: left; font-size: var(--control-font-size);
      font-weight: var(--control-font-weight); line-height: var(--control-line-height);
    }
    .ledger-switcher__dropdown button:hover { background: var(--surface-muted); }
    .ledger-switcher__dropdown button + button { margin-top: var(--space-1); }
    .ledger-switcher__menu-icon {
      width: var(--control-icon-size); height: var(--control-icon-size); display: grid; place-items: center;
      border: 2px solid var(--line-strong); border-radius: 5px; box-shadow: var(--icon-shadow);
    }
    .ledger-switcher__menu-icon--edit { background: var(--blue); color: #ffffff; }
    .ledger-switcher__menu-icon--leave { background: var(--yellow); color: #171200; }
    .ledger-main { min-width: 0; min-height: 100dvh; display: grid; align-content: start; gap: var(--space-6); padding: var(--space-6); }
    .ledger-main__header { display: flex; align-items: center; gap: var(--space-4); }
    .mobile-nav-button { display: none; }
    .ledger-main__headline { display: flex; align-items: center; gap: var(--space-4); min-width: 0; }
    .ledger-main__token { width: 48px; height: 48px; display: grid; place-items: center; border: 2px solid var(--line-strong); border-radius: 6px; box-shadow: var(--icon-shadow); }
    .ledger-main__token--green { background: var(--green); color: #07130c; }
    .ledger-main__token--yellow { background: var(--yellow); color: #171200; }
    .ledger-main__token--blue { background: var(--blue); color: #ffffff; }
    .ledger-main__token--neutral { background: var(--surface-muted); color: var(--text); }
    .ledger-main__title-wrap { min-width: 0; }
    .ledger-main__title-wrap h1 { margin: 0; font-size: clamp(1.45rem, 2vw, 1.8rem); letter-spacing: -.03em; }
    .placeholder-card { min-height: 320px; display: grid; place-items: center; align-content: center; gap: var(--space-3); padding: clamp(28px, 6vw, 52px); border: 2px solid var(--line-strong); border-radius: var(--radius-card); background: var(--surface); box-shadow: var(--shadow-hard); text-align: center; }
    .placeholder-card__actions { display: flex; flex-wrap: wrap; justify-content: center; gap: var(--space-3); margin-top: var(--space-2); }
    .placeholder-card--loading { min-height: 280px; }
    .ledger-section-content { min-height: 1px; }
    .spinner { width: 24px; height: 24px; border: 2px solid color-mix(in srgb, var(--green) 28%, var(--line)); border-top-color: var(--green-strong); border-radius: 50%; animation: spin .7s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .mobile-overlay { display: none; }
    .floating-message { position: fixed; right: 20px; bottom: 20px; width: min(430px, calc(100vw - 40px)); z-index: 80; }

    @media (max-width: 960px) {
      .ledger-shell { grid-template-columns: minmax(0, 1fr); }
      .ledger-sidebar {
        position: fixed; z-index: 40; left: 0; top: 0; bottom: 0; width: min(312px, calc(100vw - 32px)); transform: translateX(-100%);
        box-shadow: 6px 0 20px color-mix(in srgb, var(--shadow-color) 24%, transparent);
      }
      .ledger-sidebar.ledger-sidebar--mobile-open { transform: translateX(0); }
      .mobile-nav-button { display: grid; width: 48px; height: 48px; flex: 0 0 48px; }
      .ledger-main { padding: var(--space-5); }
      .mobile-overlay { position: fixed; inset: 0; display: block; z-index: 30; background: color-mix(in srgb, #000 26%, transparent); }
    }
    @media (max-width: 640px) {
      .ledger-main { gap: var(--space-5); padding: var(--space-4); }
      .ledger-main__header { align-items: center; }
      .ledger-main__headline { gap: var(--space-3); }
      .ledger-main__token, .mobile-nav-button { width: 44px; height: 44px; flex-basis: 44px; }
      .placeholder-card { min-height: 260px; padding: var(--space-5); box-shadow: var(--surface-shadow); }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerPageComponent {
  private readonly ledgers = inject(LedgerService);
  private readonly router = inject(Router);
  private readonly apiErrors = inject(ApiErrorService);
  private readonly auth = inject(AuthService);
  readonly i18n = inject(I18nService);

  readonly ledgerUuid = input.required<string>();
  readonly section = input<string | undefined>();

  readonly loading = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly mobileSidebarOpen = signal(false);
  readonly mobileActionPending = signal(false);
  readonly pendingSection = signal<LedgerSectionKey | null>(null);
  readonly preferencesOpen = signal(false);
  readonly securityOpen = signal(false);
  readonly ledgerMenuOpen = signal(false);
  readonly ledgerEditorOpen = signal(false);
  readonly loggingOut = signal(false);
  readonly logoutError = signal<string | null>(null);
  readonly isMobile = signal(typeof window !== 'undefined' ? window.innerWidth <= 960 : false);

  readonly navItems = LEDGER_SECTION_ITEMS;
  readonly currentUserName = this.auth.currentUserName.asReadonly();
  readonly activeSection = computed<LedgerSectionKey>(() => {
    const current = this.section();
    return LEDGER_SECTION_ITEMS.some((item) => item.key === current) ? current as LedgerSectionKey : 'home';
  });
  readonly currentLedger = computed(() => this.ledgers.ledgers().find((ledger) => ledger.uuid === this.ledgerUuid()) ?? null);
  readonly selectedSection = computed(() => this.pendingSection() ?? this.activeSection());
  readonly activeNavItem = computed(() => LEDGER_SECTION_ITEMS.find((item) => item.key === this.activeSection()) ?? LEDGER_SECTION_ITEMS[0]);
  readonly sectionLabel = computed(() => this.i18n.t(this.activeNavItem().labelKey));
  readonly ledgerForeground = computed(() => {
    const ledger = this.currentLedger();
    return ledger ? bestContrastingForeground(ledger.color_code).foreground : 'var(--text)';
  });

  constructor() {
    effect(() => {
      const ledgerUuid = this.ledgerUuid();
      untracked(() => this.fetchLedger(ledgerUuid));
    });
  }

  @HostListener('window:resize')
  onResize(): void {
    const mobile = window.innerWidth <= 960;
    this.isMobile.set(mobile);
    if (!mobile) {
      this.mobileSidebarOpen.set(false);
      this.mobileActionPending.set(false);
      this.pendingSection.set(null);
    }
  }

  @HostListener('document:click')
  closeLedgerMenu(): void {
    this.ledgerMenuOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.mobileSidebarOpen.set(false);
    this.mobileActionPending.set(false);
    this.pendingSection.set(null);
    this.ledgerMenuOpen.set(false);
  }

  openMobileNavigation(): void {
    if (!this.isMobile() || this.mobileSidebarOpen() || this.mobileActionPending()) return;
    this.mobileActionPending.set(true);
    window.setTimeout(() => {
      this.mobileSidebarOpen.set(true);
      this.mobileActionPending.set(false);
    }, MOBILE_NAV_ACTION_DELAY_MS);
  }

  closeMobileNavigation(): void {
    if (!this.isMobile() || this.mobileActionPending()) return;
    this.mobileActionPending.set(true);
    window.setTimeout(() => {
      this.mobileSidebarOpen.set(false);
      this.mobileActionPending.set(false);
    }, MOBILE_NAV_ACTION_DELAY_MS);
  }

  openSection(section: LedgerSectionKey): void {
    if (!this.isMobile()) {
      void this.router.navigate(['/ledgers', this.ledgerUuid(), section]);
      return;
    }
    if (this.mobileActionPending()) return;

    this.pendingSection.set(section);
    this.mobileActionPending.set(true);
    window.setTimeout(() => {
      this.mobileSidebarOpen.set(false);
      void this.router.navigate(['/ledgers', this.ledgerUuid(), section]).finally(() => {
        this.pendingSection.set(null);
        this.mobileActionPending.set(false);
      });
    }, MOBILE_NAV_ACTION_DELAY_MS);
  }

  toggleLedgerMenu(event: Event): void {
    event.stopPropagation();
    this.ledgerMenuOpen.update((value) => !value);
  }

  editCurrentLedger(): void {
    this.ledgerMenuOpen.set(false);
    this.ledgerEditorOpen.set(true);
  }

  leaveLedger(): void {
    this.ledgerMenuOpen.set(false);
    this.mobileSidebarOpen.set(false);
    this.mobileActionPending.set(false);
    this.pendingSection.set(null);
    void this.router.navigateByUrl('/home');
  }

  goHome(): void {
    this.leaveLedger();
  }

  logout(): void {
    if (this.loggingOut()) return;
    this.loggingOut.set(true);
    this.logoutError.set(null);
    this.auth.logout().pipe(finalize(() => this.loggingOut.set(false))).subscribe({
      next: () => void this.auth.finishLogout(),
      error: (error: unknown) => this.logoutError.set(this.apiErrors.message(error, 'errors.logoutFailed')),
    });
  }

  private fetchLedger(ledgerUuid: string): void {
    if (!ledgerUuid || this.loading()) return;
    this.loading.set(true);
    this.loadError.set(null);
    this.ledgers.access(ledgerUuid).pipe(finalize(() => this.loading.set(false))).subscribe({
      error: (error: unknown) => {
        this.loadError.set(this.apiErrors.message(error, 'errors.ledgerNotFound'));
      },
    });
  }
}
