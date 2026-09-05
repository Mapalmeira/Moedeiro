import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import {
  LucideArrowLeftRight,
  LucideArrowRight,
  LucideBuilding2,
  LucideBookOpen,
  LucideChartColumn,
  LucideCheck,
  LucideChevronDown,
  LucideCoins,
  LucideCopy,
  LucideDatabase,
  LucideEllipsis,
  LucideEye,
  LucideEyeOff,
  LucideHouse,
  LucideInfo,
  LucideKeyRound,
  LucideLanguages,
  LucideLayers3,
  LucideLogOut,
  LucideMail,
  LucideMoon,
  LucidePanelLeftClose,
  LucidePanelLeftOpen,
  LucidePencil,
  LucidePlus,
  LucideSearch,
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
  | 'logout' | 'sliders' | 'sun' | 'moon' | 'info' | 'check' | 'key' | 'x' | 'languages'
  | 'search' | 'chevron-down' | 'shield' | 'copy' | 'plus' | 'pencil' | 'ellipsis'
  | 'trash' | 'book' | 'database' | 'house' | 'wallet' | 'chart' | 'building'
  | 'layers' | 'coins' | 'panel-close' | 'panel-open';

@Component({
  selector: 'app-icon',
  standalone: true,
  imports: [
      LucideArrowLeftRight,
    LucideArrowRight,
    LucideBuilding2,
    LucideBookOpen,
    LucideChartColumn,
    LucideCheck,
    LucideChevronDown,
    LucideCoins,
    LucideCopy,
    LucideDatabase,
    LucideEllipsis,
    LucideEye,
    LucideEyeOff,
    LucideHouse,
    LucideInfo,
    LucideKeyRound,
    LucideLanguages,
    LucideLayers3,
    LucideLogOut,
    LucideMail,
    LucideMoon,
    LucidePanelLeftClose,
    LucidePanelLeftOpen,
    LucidePencil,
    LucidePlus,
    LucideSearch,
    LucideShieldCheck,
    LucideSlidersHorizontal,
    LucideSun,
    LucideTrash2,
    LucideUser,
    LucideWallet,
    LucideX,
  ],
  host: {
    '[style.width.px]': 'size()',
    '[style.height.px]': 'size()',
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
      @case ('key') { <svg lucideKeyRound></svg> }
      @case ('x') { <svg lucideX></svg> }
      @case ('languages') { <svg lucideLanguages></svg> }
      @case ('search') { <svg lucideSearch></svg> }
      @case ('chevron-down') { <svg lucideChevronDown></svg> }
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
      @case ('panel-close') { <svg lucidePanelLeftClose></svg> }
      @case ('panel-open') { <svg lucidePanelLeftOpen></svg> }
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
  readonly size = input(20);
}
