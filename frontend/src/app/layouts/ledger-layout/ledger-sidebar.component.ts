import { ChangeDetectionStrategy, Component, HostListener, computed, inject, input, output, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import type { Ledger } from '../../core/ledgers/ledger.models';
import { I18nService } from '../../core/i18n/i18n.service';
import { BrandLogoComponent } from '../../shared/brand/brand-logo.component';
import { bestContrastingForeground } from '../../shared/ledger/ledger-appearance';
import { LedgerIconComponent } from '../../shared/ledger/ledger-icon.component';
import { AccountMenuComponent } from '../../shared/ui/account-menu.component';
import { IconComponent } from '../../shared/ui/icon.component';
import { LEDGER_SECTION_ITEMS } from './ledger-sections';

@Component({
  selector: 'app-ledger-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, BrandLogoComponent, LedgerIconComponent, AccountMenuComponent, IconComponent],
  template: `
    <div class="ledger-sidebar__inner">
      <header class="ledger-sidebar__brand-row">
        <app-brand-logo variant="sidebar" />
      </header>

      <div class="ledger-sidebar__body">
        <nav class="ledger-nav" [attr.aria-label]="i18n.t('ledgerShell.navigation')">
          @for (item of navItems; track item.key) {
            <a
              class="ledger-nav__item"
              [class.ledger-nav__item--green]="item.tone === 'green'"
              [class.ledger-nav__item--yellow]="item.tone === 'yellow'"
              [class.ledger-nav__item--blue]="item.tone === 'blue'"
              [class.ledger-nav__item--neutral]="item.tone === 'neutral'"
              [routerLink]="['/ledgers', ledgerUuid(), item.key]"
              routerLinkActive="ledger-nav__item--active"
              [routerLinkActiveOptions]="{ exact: true }"
              ariaCurrentWhenActive="page"
              (click)="sectionSelected.emit()">
              <span class="ledger-nav__icon ui-icon-badge ui-projected-icon"
                [class.ledger-nav__icon--green]="item.tone === 'green'"
                [class.ledger-nav__icon--yellow]="item.tone === 'yellow'"
                [class.ledger-nav__icon--blue]="item.tone === 'blue'"
                [class.ledger-nav__icon--neutral]="item.tone === 'neutral'">
                <app-icon [name]="item.icon" size="action" />
              </span>
              <span class="ledger-nav__label">{{ i18n.t(item.labelKey) }}</span>
            </a>
          }
        </nav>

        <div class="ledger-sidebar__spacer"></div>

        <div class="ledger-sidebar__footer">
          @if (ledger(); as currentLedger) {
            <div class="ledger-switcher" (click)="$event.stopPropagation()">
              <button class="ledger-switcher__trigger ui-select-trigger ui-action-press ui-trigger-with-icon" type="button"
                (click)="toggleLedgerMenu($event)" [attr.aria-expanded]="ledgerMenuOpen()" [attr.aria-label]="i18n.t('ledgerShell.currentLedger') + ': ' + currentLedger.name" [attr.title]="currentLedger.name">
                <span class="ledger-switcher__icon ui-icon-badge ui-projected-icon" [style.background]="currentLedger.color_code" [style.color]="ledgerForeground()">
                  <app-ledger-icon [icon]="currentLedger.icon" [size]="20" />
                </span>
                <span class="ui-trigger-content">
                  <strong class="ledger-switcher__name ui-trigger-value ui-truncate">{{ currentLedger.name }}</strong>
                </span>
                <app-icon class="ledger-switcher__chevron ui-select-chevron" name="chevron-down" size="chevron" />
              </button>

              @if (ledgerMenuOpen()) {
                <div class="ledger-switcher__dropdown ui-dropdown-menu ui-projected-surface ui-projection--compact" role="menu">
                  <button type="button" role="menuitem" (click)="editCurrentLedger()">
                    <span class="ledger-switcher__menu-icon ledger-switcher__menu-icon--edit ui-icon-badge ui-projected-icon"><app-icon name="pencil" size="menu" /></span>
                    <span>{{ i18n.t('ledgers.edit') }}</span>
                  </button>
                  <button type="button" role="menuitem" (click)="leaveCurrentLedger()">
                    <span class="ledger-switcher__menu-icon ledger-switcher__menu-icon--leave ui-icon-badge ui-projected-icon"><app-icon name="logout" size="menu" /></span>
                    <span>{{ i18n.t('ledgerShell.leave') }}</span>
                  </button>
                </div>
              }
            </div>
          }

          <app-account-menu
            [userName]="userName()"
            [label]="i18n.t('ledgerShell.myAccount')"
            [loggingOut]="loggingOut()"
            placement="up"
            [fullWidth]="true"
            (preferences)="preferences.emit()"
            (security)="security.emit()"
            (logout)="logout.emit()" />
        </div>
      </div>
    </div>
  `,
  styles: `
    :host { display: block; height: 100%; min-height: 0; }
    .ledger-sidebar__inner { height: 100%; min-height: 0; display: grid; grid-template-rows: var(--ledger-header-height) minmax(0, 1fr); }
    .ledger-sidebar__brand-row { width: 100%; display: grid; place-items: center; border-bottom: var(--border-width) solid var(--line); }
    .ledger-sidebar__brand-row app-brand-logo { width: max-content; }
    .ledger-sidebar__body { min-height: 0; display: flex; flex-direction: column; gap: var(--space-6); padding: var(--space-5) var(--space-4); overflow-x: hidden; overflow-y: auto; overscroll-behavior: contain; }
    .ledger-nav { display: grid; gap: var(--space-2); }
    .ledger-nav__item {
      position: relative;
      min-height: var(--sidebar-control-height); display: grid; grid-template-columns: var(--control-icon-footprint) minmax(0, 1fr); align-items: center; gap: var(--space-3);
      padding: var(--space-2) var(--control-padding-inline); border: var(--border-width) solid transparent; border-radius: var(--radius-sm); background: transparent; color: var(--text);
      text-align: left; text-decoration: none; font-size: var(--control-font-size); font-weight: var(--control-font-weight); line-height: var(--control-line-height); box-shadow: var(--selection-shadow-transparent); transition: box-shadow var(--motion-selection) ease, background var(--motion-selection) ease, border-color var(--motion-selection) ease;
    }
    .ledger-nav__item:not(.ledger-nav__item--active):hover { background: var(--surface-muted); }
    .ledger-nav__item--green { --ledger-nav-active-background: var(--green-soft); }
    .ledger-nav__item--yellow { --ledger-nav-active-background: var(--yellow-soft); }
    .ledger-nav__item--blue { --ledger-nav-active-background: var(--blue-soft); }
    .ledger-nav__item--neutral { --ledger-nav-active-background: var(--surface-muted); }
    .ledger-nav__item--active { border-color: var(--line-strong); background: var(--ledger-nav-active-background, var(--surface-muted)); color: var(--text); box-shadow: var(--selection-shadow); }
    .ledger-nav__icon--green { background: var(--green); color: var(--on-green); }
    .ledger-nav__icon--yellow { background: var(--yellow); color: var(--on-yellow); }
    .ledger-nav__icon--blue { background: var(--blue); color: var(--on-blue); }
    .ledger-nav__icon--neutral { background: var(--surface-muted); color: var(--text); }
    .ledger-nav__label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .ledger-sidebar__spacer { flex: 1 1 auto; }
    .ledger-sidebar__footer { display: grid; gap: var(--space-3); }
    .ledger-switcher { position: relative; min-width: 0; }
    .ledger-switcher__trigger {
      width: 100%; min-width: 0; min-height: var(--sidebar-control-height); text-align: left;
    }
    .ledger-switcher__name { font: inherit; }
    .ledger-switcher__chevron { justify-self: end; }
    .ledger-switcher__dropdown {
      position: absolute; z-index: var(--layer-dropdown); left: 0; right: 0; bottom: calc(100% + var(--space-2));
    }
    .ledger-switcher__dropdown button {
      width: 100%; min-height: var(--menu-item-height); display: grid; grid-template-columns: var(--control-icon-footprint) minmax(0, 1fr);
      align-items: center; gap: var(--space-3); padding: var(--space-2); border: 0; border-radius: var(--radius-sm);
      background: transparent; color: var(--text); text-align: left; font-size: var(--control-font-size);
      font-weight: var(--control-font-weight); line-height: var(--control-line-height);
    }
    .ledger-switcher__dropdown button:hover { background: var(--surface-muted); }
    .ledger-switcher__dropdown button + button { margin-top: var(--space-1); }
    .ledger-switcher__menu-icon--edit { background: var(--blue); color: var(--on-blue); }
    .ledger-switcher__menu-icon--leave { background: var(--yellow); color: var(--on-yellow); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerSidebarComponent {
  readonly i18n = inject(I18nService);

  readonly ledgerUuid = input.required<string>();
  readonly ledger = input<Ledger | null>(null);
  readonly userName = input<string | null>(null);
  readonly loggingOut = input(false);
  readonly sectionSelected = output<void>();
  readonly editLedger = output<void>();
  readonly leaveLedger = output<void>();
  readonly preferences = output<void>();
  readonly security = output<void>();
  readonly logout = output<void>();

  readonly navItems = LEDGER_SECTION_ITEMS;
  readonly ledgerMenuOpen = signal(false);
  readonly ledgerForeground = computed(() => {
    const currentLedger = this.ledger();
    return currentLedger ? bestContrastingForeground(currentLedger.color_code) : 'var(--text)';
  });

  @HostListener('document:click')
  closeLedgerMenu(): void {
    this.ledgerMenuOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.ledgerMenuOpen.set(false);
  }

  toggleLedgerMenu(event: Event): void {
    event.stopPropagation();
    this.ledgerMenuOpen.update((value) => !value);
  }

  editCurrentLedger(): void {
    this.ledgerMenuOpen.set(false);
    this.editLedger.emit();
  }

  leaveCurrentLedger(): void {
    this.ledgerMenuOpen.set(false);
    this.leaveLedger.emit();
  }
}
