import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import {
  LucideArrowLeftRight,
  LucideArrowRight,
  LucideBuilding2,
  LucideBookOpen,
  LucideCalendarDays,
  LucideChartColumn,
  LucideCheck,
  LucideClock,
  LucideChevronDown,
  LucideChevronLeft,
  LucideChevronRight,
  LucideCoins,
  LucideCopy,
  LucideDatabase,
  LucideEllipsis,
  LucideEye,
  LucideEyeOff,
  LucideFolder,
  LucideGripVertical,
  LucideHouse,
  LucideInfo,
  LucideKeyRound,
  LucideLanguages,
  LucideLayers3,
  LucideLogOut,
  LucideMail,
  LucideMoon,
  LucidePanelLeftOpen,
  LucidePencil,
  LucidePlus,
  LucideSearch,
  LucideShoppingCart,
  LucideShieldCheck,
  LucideSlidersHorizontal,
  LucideSun,
  LucideTrash2,
  LucideUser,
  LucideWallet,
  LucideX,
} from '@lucide/angular';

export type IconName =
  | 'user' | 'mail' | 'eye' | 'eye-off' | 'arrow-right' | 'arrow-left-right'
  | 'logout' | 'sliders' | 'sun' | 'moon' | 'info' | 'check' | 'clock' | 'key' | 'x' | 'languages'
  | 'search' | 'chevron-down' | 'chevron-left' | 'chevron-right' | 'calendar' | 'shield' | 'copy' | 'plus' | 'pencil' | 'ellipsis'
  | 'trash' | 'book' | 'database' | 'house' | 'wallet' | 'chart' | 'building'
  | 'layers' | 'coins' | 'panel-open' | 'folder' | 'grip' | 'shopping-cart';


export type IconSize =
  | 'indicator'
  | 'chevron'
  | 'selection'
  | 'menu'
  | 'compact-control'
  | 'action'
  | 'close'
  | 'navigation'
  | 'dialog-title'
  | 'metric'
  | 'badge-symbol'
  | 'card-title'
  | 'empty-state';

const ICON_SIZE_VARIABLES: Record<IconSize, string> = {
  indicator: '--icon-glyph-indicator',
  chevron: '--icon-glyph-compact',
  selection: '--icon-glyph-compact',
  menu: '--icon-glyph-control',
  'compact-control': '--icon-glyph-control',
  action: '--icon-glyph-control',
  close: '--icon-glyph-control',
  navigation: '--icon-glyph-prominent',
  'dialog-title': '--icon-glyph-prominent',
  metric: '--icon-glyph-prominent',
  'badge-symbol': '--icon-glyph-badge',
  'card-title': '--icon-glyph-badge',
  'empty-state': '--icon-glyph-display',
};

@Component({
  selector: 'app-icon',
  standalone: true,
  imports: [
    LucideArrowLeftRight,
    LucideArrowRight,
    LucideBuilding2,
    LucideBookOpen,
    LucideCalendarDays,
    LucideChartColumn,
    LucideCheck,
    LucideClock,
    LucideChevronDown,
    LucideChevronLeft,
    LucideChevronRight,
    LucideCoins,
    LucideCopy,
    LucideDatabase,
    LucideEllipsis,
    LucideEye,
    LucideEyeOff,
    LucideFolder,
    LucideGripVertical,
    LucideHouse,
    LucideInfo,
    LucideKeyRound,
    LucideLanguages,
    LucideLayers3,
    LucideLogOut,
    LucideMail,
    LucideMoon,
    LucidePanelLeftOpen,
    LucidePencil,
    LucidePlus,
    LucideSearch,
    LucideShoppingCart,
    LucideShieldCheck,
    LucideSlidersHorizontal,
    LucideSun,
    LucideTrash2,
    LucideUser,
    LucideWallet,
    LucideX,
  ],
  host: {
    '[style.width]': 'resolvedSize()',
    '[style.height]': 'resolvedSize()',
  },
  template: `
    @switch (name()) {
      @case ('user') { <svg lucideUser></svg> }
      @case ('mail') { <svg lucideMail></svg> }
      @case ('eye') { <svg lucideEye></svg> }
      @case ('eye-off') { <svg lucideEyeOff></svg> }
      @case ('arrow-right') { <svg lucideArrowRight></svg> }
      @case ('arrow-left-right') { <svg lucideArrowLeftRight></svg> }
      @case ('logout') { <svg lucideLogOut></svg> }
      @case ('sliders') { <svg lucideSlidersHorizontal></svg> }
      @case ('sun') { <svg lucideSun></svg> }
      @case ('moon') { <svg lucideMoon></svg> }
      @case ('info') { <svg lucideInfo></svg> }
      @case ('check') { <svg lucideCheck></svg> }
      @case ('clock') { <svg lucideClock></svg> }
      @case ('key') { <svg lucideKeyRound></svg> }
      @case ('x') { <svg lucideX></svg> }
      @case ('languages') { <svg lucideLanguages></svg> }
      @case ('search') { <svg lucideSearch></svg> }
      @case ('shopping-cart') { <svg lucideShoppingCart></svg> }
      @case ('chevron-down') { <svg lucideChevronDown></svg> }
      @case ('chevron-left') { <svg lucideChevronLeft></svg> }
      @case ('chevron-right') { <svg lucideChevronRight></svg> }
      @case ('calendar') { <svg lucideCalendarDays></svg> }
      @case ('shield') { <svg lucideShieldCheck></svg> }
      @case ('copy') { <svg lucideCopy></svg> }
      @case ('plus') { <svg lucidePlus></svg> }
      @case ('pencil') { <svg lucidePencil></svg> }
      @case ('ellipsis') { <svg lucideEllipsis></svg> }
      @case ('trash') { <svg lucideTrash2></svg> }
      @case ('book') { <svg lucideBookOpen></svg> }
      @case ('database') { <svg lucideDatabase></svg> }
      @case ('house') { <svg lucideHouse></svg> }
      @case ('wallet') { <svg lucideWallet></svg> }
      @case ('chart') { <svg lucideChartColumn></svg> }
      @case ('building') { <svg lucideBuilding2></svg> }
      @case ('layers') { <svg lucideLayers3></svg> }
      @case ('coins') { <svg lucideCoins></svg> }
      @case ('panel-open') { <svg lucidePanelLeftOpen></svg> }
      @case ('folder') { <svg lucideFolder></svg> }
      @case ('grip') { <svg lucideGripVertical></svg> }
    }
  `,
  styles: `
    :host { display: inline-grid; place-items: center; flex: 0 0 auto; line-height: 0; vertical-align: middle; }
    svg { display: block; width: 100%; height: 100%; fill: none; stroke: currentColor; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IconComponent {
  readonly name = input.required<IconName>();
  readonly size = input<IconSize | number>('action');
  readonly resolvedSize = computed(() => {
    const size = this.size();
    return typeof size === 'number' ? `${size}px` : `var(${ICON_SIZE_VARIABLES[size]})`;
  });
}
