import { ChangeDetectionStrategy, Component, HostListener, computed, effect, inject, input, signal } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter } from 'rxjs';
import { LedgerContextService } from '../../core/ledgers/ledger-context.service';
import { AuthenticatedShellService } from '../authenticated-layout/authenticated-shell.service';
import { I18nService } from '../../core/i18n/i18n.service';
import { LedgerEditorDialogComponent } from '../../features/ledgers/ledger-editor-dialog.component';
import { FormMessageComponent } from '../../shared/ui/form-message.component';
import { IconComponent } from '../../shared/ui/icon.component';
import { LedgerSidebarComponent } from './ledger-sidebar.component';
import { ledgerSectionByKey } from './ledger-sections';

@Component({
  selector: 'app-ledger-layout',
  standalone: true,
  imports: [RouterOutlet, LedgerSidebarComponent, LedgerEditorDialogComponent, FormMessageComponent, IconComponent],
  template: `
    <div class="ledger-shell">
      @if (isMobile() && mobileSidebarOpen()) {
        <button class="mobile-overlay" type="button" (click)="closeMobileNavigation()" [attr.aria-label]="i18n.t('ledgerShell.collapse')"></button>
      }

      <aside class="ledger-sidebar" [class.ledger-sidebar--mobile-open]="mobileSidebarOpen()">
        <app-ledger-sidebar
          [ledgerUuid]="ledgerUuid()"
          [ledger]="context.ledger()"
          [userName]="shell.currentUserName()"
          [loggingOut]="shell.loggingOut()"
          (sectionSelected)="onSectionSelected()"
          (editLedger)="ledgerEditorOpen.set(true)"
          (leaveLedger)="leaveLedger()"
          (preferences)="shell.openPreferences()"
          (security)="shell.openSecurity()"
          (logout)="shell.logout()" />
      </aside>

      <section class="ledger-main">
        <header class="ledger-main__header">
          <button class="mobile-nav-button ui-action-press" type="button" (click)="openMobileNavigation()"
            [attr.aria-label]="i18n.t('ledgerShell.navigation')">
            <app-icon name="panel-open" [size]="20" />
          </button>

          <div class="ledger-main__headline ui-heading-with-icon">
            <span class="ledger-main__token ui-icon-badge ui-icon-badge--title ui-projected-icon"
              [class.ledger-main__token--green]="activeSection().tone === 'green'"
              [class.ledger-main__token--yellow]="activeSection().tone === 'yellow'"
              [class.ledger-main__token--blue]="activeSection().tone === 'blue'"
              [class.ledger-main__token--neutral]="activeSection().tone === 'neutral'">
              <app-icon [name]="activeSection().icon" [size]="20" />
            </span>
            <div class="ledger-main__title-wrap">
              <h1>{{ i18n.t(activeSection().labelKey) }}</h1>
            </div>
          </div>
        </header>

        @if (context.loadError()) {
          <div class="placeholder-card placeholder-card--error ui-projected-surface ui-projection--hard">
            <app-form-message [text]="context.loadError()!" />
            <div class="placeholder-card__actions">
              <button class="ui-button ui-button--green" type="button" (click)="leaveLedger()">{{ i18n.t('ledgerShell.backToLedgers') }}</button>
            </div>
          </div>
        } @else if (context.loading() && !context.ledger()) {
          <div class="placeholder-card placeholder-card--loading ui-projected-surface ui-projection--hard">
            <div class="spinner ui-spinner" aria-hidden="true"></div>
          </div>
        } @else {
          <div class="ledger-section-content" aria-live="polite">
            <router-outlet />
          </div>
        }
      </section>

      <app-ledger-editor-dialog
        [open]="ledgerEditorOpen()"
        [ledger]="context.ledger()"
        (close)="ledgerEditorOpen.set(false)"
        (saved)="ledgerEditorOpen.set(false)" />
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
      border-right: var(--border-width) solid var(--line);
      background: var(--surface);
      transition: transform var(--motion-disclosure) ease;
      overflow: hidden;
    }
    .ledger-main { min-width: 0; min-height: 100dvh; display: grid; align-content: start; gap: var(--space-6); padding: var(--space-6); }
    .ledger-main__header { display: flex; align-items: center; gap: var(--space-4); }
    .mobile-nav-button {
      display: none; place-items: center; width: var(--icon-button-size); height: var(--icon-button-size); padding: 0; border: var(--border-width) solid var(--line-strong);
      border-radius: var(--radius-sm); background: var(--surface); color: var(--text);
    }
    .mobile-nav-button:hover { background: var(--surface-muted); }
    .ledger-main__headline { min-height: calc(var(--title-icon-size) + var(--icon-shadow-offset)); }
    .ledger-main__token { border-radius: var(--radius-sm); }
    .ledger-main__token--green { background: var(--green); color: var(--on-green); }
    .ledger-main__token--yellow { background: var(--yellow); color: var(--on-yellow); }
    .ledger-main__token--blue { background: var(--blue); color: var(--on-blue); }
    .ledger-main__token--neutral { background: var(--surface-muted); color: var(--text); }
    .ledger-main__title-wrap { min-width: 0; }
    .ledger-main__title-wrap h1 { margin: 0; font-size: clamp(1.45rem, 2vw, 1.8rem); line-height: var(--heading-line-height); letter-spacing: -.03em; }
    .placeholder-card { min-height: 320px; display: grid; place-items: center; align-content: center; gap: var(--space-3); padding: clamp(28px, 6vw, 52px); border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-card); background: var(--surface); text-align: center; }
    .placeholder-card__actions { display: flex; flex-wrap: wrap; justify-content: center; gap: var(--space-3); margin-top: var(--space-2); }
    .placeholder-card--loading { min-height: 280px; }
    .ledger-section-content { min-height: 1px; }
    .spinner { --spinner-size: 24px; }
    .mobile-overlay { display: none; }

    @media (max-width: 960px) {
      .ledger-shell { grid-template-columns: minmax(0, 1fr); }
      .ledger-sidebar {
        position: fixed; z-index: var(--layer-drawer); left: 0; top: 0; bottom: 0; width: min(312px, calc(100vw - 32px)); transform: translateX(-100%);
        box-shadow: var(--drawer-shadow);
      }
      .ledger-sidebar.ledger-sidebar--mobile-open { transform: translateX(0); }
      .mobile-nav-button { display: grid; width: var(--touch-target-size); height: var(--touch-target-size); flex: 0 0 var(--touch-target-size); }
      .ledger-main { padding: var(--space-5); }
      .mobile-overlay { position: fixed; inset: 0; display: block; z-index: var(--layer-drawer-backdrop); background: var(--drawer-overlay-color); }
    }
    @media (max-width: 640px) {
      .ledger-main { gap: var(--space-5); padding: var(--space-4); }
      .ledger-main__header { align-items: center; }
      .ledger-main__headline { gap: var(--space-3); }
      .placeholder-card { box-shadow: var(--surface-shadow); min-height: 260px; padding: var(--space-5); }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerLayoutComponent {
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly navigationEnd = toSignal(
    this.router.events.pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd)),
    { initialValue: null },
  );

  readonly context = inject(LedgerContextService);
  readonly shell = inject(AuthenticatedShellService);
  readonly i18n = inject(I18nService);
  readonly ledgerUuid = input.required<string>();

  readonly mobileSidebarOpen = signal(false);
  readonly ledgerEditorOpen = signal(false);
  readonly isMobile = signal(typeof window !== 'undefined' ? window.innerWidth <= 960 : false);
  readonly activeSection = computed(() => {
    this.navigationEnd();
    return ledgerSectionByKey(this.route.firstChild?.snapshot.data['ledgerSection']);
  });

  constructor() {
    effect(() => this.context.load(this.ledgerUuid()));
  }

  @HostListener('window:resize')
  onResize(): void {
    const mobile = window.innerWidth <= 960;
    this.isMobile.set(mobile);
    if (!mobile) {
      this.mobileSidebarOpen.set(false);
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.mobileSidebarOpen.set(false);
  }

  openMobileNavigation(): void {
    if (!this.isMobile() || this.mobileSidebarOpen()) return;
    this.mobileSidebarOpen.set(true);
  }

  closeMobileNavigation(): void {
    if (!this.isMobile() || !this.mobileSidebarOpen()) return;
    this.mobileSidebarOpen.set(false);
  }

  onSectionSelected(): void {
    if (this.isMobile()) this.closeMobileNavigation();
  }

  leaveLedger(): void {
    this.mobileSidebarOpen.set(false);
    void this.router.navigateByUrl('/home');
  }
}
