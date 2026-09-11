import { ChangeDetectionStrategy, Component, inject, input, output, signal } from '@angular/core';
import { DismissiblePopoverDirective } from './dismissible-popover.directive';
import { I18nService } from '../../core/i18n/i18n.service';
import { IconComponent } from './icon.component';

@Component({
  selector: 'app-account-menu',
  standalone: true,
  imports: [DismissiblePopoverDirective, IconComponent],
  host: {
    '[class.account-menu-host--full]': 'fullWidth()',
  },
  template: `
    <div class="account-control" [class.account-control--up]="placement() === 'up'" [appDismissiblePopover]="open()" (dismiss)="open.set(false)">
      <button class="account-trigger ui-select-trigger ui-action-press ui-trigger-with-icon" type="button" (click)="toggle($event)"
        [attr.aria-expanded]="open()" [attr.aria-label]="label() ? label() + ': ' + (userName() || '—') : i18n.t('shell.settings')">
        <span class="account-trigger__icon ui-icon-badge ui-projected-icon"><app-icon name="LucideUser" size="control" /></span>
        <span class="ui-trigger-content">
          <strong class="account-trigger__name ui-trigger-value ui-truncate">{{ userName() || '—' }}</strong>
          @if (label(); as controlLabel) { <span class="ui-trigger-context">{{ controlLabel }}</span> }
        </span>
        <app-icon class="account-trigger__chevron ui-select-chevron" name="LucideChevronDown" size="compact" />
      </button>

      @if (open()) {
        <div class="account-dropdown ui-dropdown-menu ui-projected-surface ui-projection--compact" role="menu" (click)="$event.stopPropagation()">
          <button type="button" role="menuitem" (click)="choosePreferences()">
            <span class="account-dropdown__icon account-dropdown__icon--green ui-icon-badge ui-projected-icon"><app-icon name="LucideSlidersHorizontal" size="control" /></span>
            <span>{{ i18n.t('shell.preferences') }}</span>
          </button>
          <button type="button" role="menuitem" (click)="chooseSecurity()">
            <span class="account-dropdown__icon account-dropdown__icon--blue ui-icon-badge ui-projected-icon"><app-icon name="LucideShieldCheck" size="control" /></span>
            <span>{{ i18n.t('shell.security') }}</span>
          </button>
          <button type="button" role="menuitem" (click)="chooseLogout()" [disabled]="loggingOut()">
            <span class="account-dropdown__icon account-dropdown__icon--yellow ui-icon-badge ui-projected-icon"><app-icon name="LucideLogOut" size="control" /></span>
            <span>{{ i18n.t('shell.logout') }}</span>
          </button>
        </div>
      }
    </div>
  `,
  styles: `
    :host { display: inline-block; min-width: 0; }
    :host.account-menu-host--full { display: block; width: 100%; }
    .account-control { position: relative; width: 100%; min-width: 0; }
    .account-trigger {
      width: 100%;
      min-width: 0;
      min-height: var(--sidebar-control-height);
      text-align: left;
      font-size: var(--control-font-size);
      font-weight: var(--control-font-weight);
      line-height: var(--control-line-height);
    }
    .account-trigger__icon {
      background: var(--green);
      color: var(--on-green);
    }
    .account-trigger__name {
      font: inherit;
    }
    .account-trigger__chevron { justify-self: end; display: inline-grid; }
    .account-dropdown {
      box-sizing: border-box;
      position: absolute;
      z-index: var(--layer-dropdown);
      top: calc(100% + var(--space-2));
      right: 0;
      width: 100%;
    }
    .account-control--up .account-dropdown { top: auto; bottom: calc(100% + var(--space-2)); left: 0; right: auto; }
    .account-dropdown button {
      width: 100%;
      min-height: var(--menu-item-height);
      display: grid;
      grid-template-columns: var(--control-icon-footprint) minmax(0, 1fr);
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-2);
      border: 0;
      border-radius: var(--radius-sm);
      background: transparent;
      color: var(--text);
      text-align: left;
      font-size: var(--control-font-size);
      font-weight: var(--control-font-weight);
      line-height: var(--control-line-height);
    }
    .account-dropdown button:not(:disabled):hover { background: var(--surface-muted); }
    .account-dropdown button + button { margin-top: var(--space-1); }
    .account-dropdown__icon--green { background: var(--green); color: var(--on-green); }
    .account-dropdown__icon--blue { background: var(--blue); color: var(--on-blue); }
    .account-dropdown__icon--yellow { background: var(--yellow); color: var(--on-yellow); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccountMenuComponent {
  readonly i18n = inject(I18nService);

  readonly userName = input<string | null>(null);
  readonly label = input<string | null>(null);
  readonly loggingOut = input(false);
  readonly placement = input<'up' | 'down'>('down');
  readonly fullWidth = input(false);

  readonly preferences = output<void>();
  readonly security = output<void>();
  readonly logout = output<void>();
  readonly open = signal(false);

  toggle(event: Event): void {
    event.stopPropagation();
    this.open.update((value) => !value);
  }

  choosePreferences(): void {
    this.open.set(false);
    this.preferences.emit();
  }

  chooseSecurity(): void {
    this.open.set(false);
    this.security.emit();
  }

  chooseLogout(): void {
    this.open.set(false);
    this.logout.emit();
  }
}
