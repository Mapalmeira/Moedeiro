import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { LucideDynamicIcon } from '@lucide/angular';
import { resolveLucideIcon } from './lucide-icon-catalog';
import {
  decodeLucideLedgerIcon,
  decodeUnicodeLedgerIcon,
  isEncodedLucideLedgerIcon,
} from './ledger-icon-value';

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
      <span class="unicode-icon" aria-hidden="true">{{ unicodeValue() }}</span>
    }
  `,
  styles: `
    :host {
      position: relative;
      display: inline-grid;
      place-items: center;
      flex: 0 0 auto;
      line-height: 1;
      overflow: visible;
    }
    svg { display: block; width: 100%; height: 100%; fill: none; stroke: currentColor; }
    .unicode-icon {
      position: absolute;
      top: 50%;
      left: 50%;
      display: block;
      width: max-content;
      transform: translate(-50%, -50%);
      transform-origin: center;
      font-family: inherit;
      font-size: .7em;
      font-kerning: normal;
      letter-spacing: 0;
      line-height: 1;
      text-align: center;
      white-space: nowrap;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerIconComponent {
  readonly icon = input.required<string>();
  readonly size = input(22);
  readonly lucideComponent = computed(() => {
    const value = this.icon();
    return isEncodedLucideLedgerIcon(value) ? resolveLucideIcon(decodeLucideLedgerIcon(value)) : null;
  });
  readonly unicodeValue = computed(() => decodeUnicodeLedgerIcon(this.icon()));
}
