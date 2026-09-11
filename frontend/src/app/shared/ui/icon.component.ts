import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { icons, LucideDynamicIcon } from '@lucide/angular';

export type IconName = keyof typeof icons;

type IconSize =
  | 'indicator'
  | 'compact'
  | 'control'
  | 'prominent'
  | 'badge'
  | 'display';

@Component({
  selector: 'app-icon',
  standalone: true,
  imports: [LucideDynamicIcon],
  host: {
    '[style.width]': 'resolvedSize()',
    '[style.height]': 'resolvedSize()',
  },
  template: `<svg [lucideIcon]="icon()" aria-hidden="true"></svg>`,
  styles: `
    :host { display: inline-grid; place-items: center; flex: 0 0 auto; line-height: 0; vertical-align: middle; }
    svg { display: block; width: 100%; height: 100%; fill: none; stroke: currentColor; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IconComponent {
  readonly name = input.required<IconName>();
  readonly size = input<IconSize>('control');
  readonly icon = computed(() => icons[this.name()]);
  readonly resolvedSize = computed(() => `var(--icon-glyph-${this.size()})`);
}
