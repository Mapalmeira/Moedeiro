import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { bestContrastingForeground } from './ledger-appearance';
import { LedgerIconComponent } from './ledger-icon.component';

/** Clip the face, keeping the projected shadow and its layout footprint intact. */
@Component({
  selector: 'app-entity-badge',
  imports: [LedgerIconComponent],
  template: `<span class="badge ui-projected-icon" [style.width.px]="size()" [style.height.px]="size()"
    [style.background]="color()" [style.color]="foreground(color())">
    <app-ledger-icon [icon]="icon()" [size]="size() * symbolRatio" />
  </span>`,
  styles: `
    :host { display: inline-flex; flex: 0 0 auto; }
    .badge { display: grid; place-items: center; overflow: hidden; border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-icon); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityBadgeComponent {
  readonly icon = input.required<string>();
  readonly color = input.required<string>();
  readonly size = input(30);
  readonly symbolRatio = 23 / 30;
  foreground(color: string): string { return bestContrastingForeground(color).foreground; }
}
