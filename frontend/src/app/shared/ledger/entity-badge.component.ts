import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { bestContrastingForeground } from './ledger-appearance';
import { LedgerIconComponent } from './ledger-icon.component';

const ENTITY_BADGE_DEFAULT_SIZE = 30;
const ENTITY_BADGE_DEFAULT_SYMBOL_SIZE = 23;

/** Clip the face, keeping the projected shadow and its layout footprint intact. */
@Component({
  selector: 'app-entity-badge',
  imports: [LedgerIconComponent],
  template: `<span class="badge ui-projected-icon" [style.width.px]="size()" [style.height.px]="size()"
    [style.background]="color()" [style.color]="foreground()">
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
  readonly size = input(ENTITY_BADGE_DEFAULT_SIZE);
  readonly symbolRatio = ENTITY_BADGE_DEFAULT_SYMBOL_SIZE / ENTITY_BADGE_DEFAULT_SIZE;
  readonly foreground = computed(() => bestContrastingForeground(this.color()));
}
