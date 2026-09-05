import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { LucideDynamicIcon } from '@lucide/angular';
import { resolveLucideIcon } from './lucide-icon-catalog';
import { decodeUnicodeLedgerIcon, isEncodedUnicodeLedgerIcon } from './ledger-icon-value';

@Component({
  selector: 'app-ledger-icon',
  standalone: true,
  imports: [LucideDynamicIcon],
  host: {
    '[style.width.px]': 'size()',
    '[style.height.px]': 'size()',
    '[style.font-size.px]': 'size()',
  },
  template: `
    @if (lucideComponent(); as component) {
      <svg [lucideIcon]="component" aria-hidden="true"></svg>
    } @else {
      <span class="unicode-icon" [class.unicode-icon--two]="unicodeLength() === 2" [class.unicode-icon--three]="unicodeLength() >= 3" aria-hidden="true">{{ unicodeValue() }}</span>
    }
  `,
  styles: `
    :host { display: inline-grid; place-items: center; flex: 0 0 auto; line-height: 1; }
    svg { display: block; width: 100%; height: 100%; fill: none; stroke: currentColor; }
    .unicode-icon { width: 100%; height: 100%; max-width: 100%; display: flex; align-items: center; justify-content: center; overflow: hidden; padding-inline: 1px; font-size: .72em; line-height: 1; text-align: center; white-space: nowrap; }
    .unicode-icon--two { font-size: .52em; }
    .unicode-icon--three { font-size: .36em; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerIconComponent {
  readonly icon = input.required<string>();
  readonly size = input(22);
  readonly lucideComponent = computed(() => isEncodedUnicodeLedgerIcon(this.icon()) ? null : resolveLucideIcon(this.icon()));
  readonly unicodeValue = computed(() => decodeUnicodeLedgerIcon(this.icon()));
  readonly unicodeLength = computed(() => Array.from(this.unicodeValue()).length);
}
