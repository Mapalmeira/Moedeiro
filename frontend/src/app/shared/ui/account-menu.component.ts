import { ChangeDetectionStrategy, Component, ElementRef, HostListener, inject, input, output, signal } from '@angular/core';
import { I18nService } from '../../core/i18n/i18n.service';
import { IconComponent } from './icon.component';

@Component({
  selector: 'app-account-menu',
  standalone: true,
  imports: [IconComponent],
  host: {
    '[class.account-menu-host--full]': 'fullWidth()',
  },
  template: `
    <div class="account-control" [class.account-control--up]="placement() === 'up'">
      <button class="account-trigger ui-select-trigger ui-action-press" type="button" (click)="toggle($event)"
        [attr.aria-expanded]="open()" [attr.aria-label]="i18n.t('shell.settings')">
        <span class="account-trigger__icon ui-projected-icon"><app-icon name="user" [size]="17" /></span>
        <strong class="account-trigger__name">{{ userName() || '—' }}</strong>
        <app-icon class="account-trigger__chevron ui-select-chevron" name="chevron-down" [size]="16" />
      </button>

      @if (open()) {
        <div class="account-dropdown" role="menu" (click)="$event.stopPropagation()">
          <button type="button" role="menuitem" (click)="choosePreferences()">
            <span class="account-dropdown__icon account-dropdown__icon--green ui-projected-icon"><app-icon name="sliders" [size]="17" /></span>
            <span>{{ i18n.t('shell.preferences') }}</span>
          </button>
          <button type="button" role="menuitem" (click)="chooseSecurity()">
            <span class="account-dropdown__icon account-dropdown__icon--blue ui-projected-icon"><app-icon name="shield" [size]="17" /></span>
            <span>{{ i18n.t('shell.security') }}</span>
          </button>
          <button type="button" role="menuitem" (click)="chooseLogout()" [disabled]="loggingOut()">
            <span class="account-dropdown__icon account-dropdown__icon--yellow ui-projected-icon"><app-icon name="logout" [size]="17" /></span>
            <span>{{ loggingOut() ? i18n.t('shell.loggingOut') : i18n.t('shell.logout') }}</span>
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
      display: grid;
      grid-template-columns: var(--control-icon-size) minmax(0, 1fr) 16px;
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-2) var(--space-3);
      text-align: left;
      font-size: var(--control-font-size);
      font-weight: var(--control-font-weight);
      line-height: var(--control-line-height);
    }
    .account-trigger__icon {
      width: var(--control-icon-size);
      height: var(--control-icon-size);
      display: grid;
      place-items: center;
      border: 2px solid var(--line-strong);
      border-radius: 5px;
      background: var(--green);
      color: #050505;
    }
    .account-trigger__name {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: inherit;
      font-weight: inherit;
      line-height: inherit;
    }
    .account-trigger__chevron { justify-self: end; display: inline-grid; }
    .account-dropdown {
      box-sizing: border-box;
      position: absolute;
      z-index: 90;
      top: calc(100% + var(--space-2));
      right: 0;
      width: 100%;
      padding: var(--space-2);
      border: 2px solid var(--line-strong);
      border-radius: 8px;
      background: var(--surface);
      filter: var(--compact-button-shadow);
    }
    .account-control--up .account-dropdown { top: auto; bottom: calc(100% + var(--space-2)); left: 0; right: auto; }
    .account-dropdown button {
      width: 100%;
      min-height: var(--control-height);
      display: grid;
      grid-template-columns: var(--control-icon-size) minmax(0, 1fr);
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-2);
      border: 0;
      border-radius: 5px;
      background: transparent;
      color: var(--text);
      text-align: left;
      font-size: var(--control-font-size);
      font-weight: var(--control-font-weight);
      line-height: var(--control-line-height);
    }
    .account-dropdown button:not(:disabled):hover { background: var(--surface-muted); }
    .account-dropdown button + button { margin-top: var(--space-1); }
    .account-dropdown__icon {
      width: var(--control-icon-size);
      height: var(--control-icon-size);
      display: grid;
      place-items: center;
      border: 2px solid var(--line-strong);
      border-radius: 5px;
    }
    .account-dropdown__icon--green { background: var(--green); color: #07130c; }
    .account-dropdown__icon--blue { background: var(--blue); color: var(--on-blue); }
    .account-dropdown__icon--yellow { background: var(--yellow); color: #171200; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccountMenuComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  readonly i18n = inject(I18nService);

  readonly userName = input<string | null>(null);
  readonly loggingOut = input(false);
  readonly placement = input<'up' | 'down'>('down');
  readonly fullWidth = input(false);

  readonly preferences = output<void>();
  readonly security = output<void>();
  readonly logout = output<void>();
  readonly open = signal(false);

  @HostListener('document:mousedown', ['$event'])
  closeWhenClickingOutside(event: MouseEvent): void {
    if (!this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }

  @HostListener('document:keydown.escape')
  closeOnEscape(): void {
    this.open.set(false);
  }

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
