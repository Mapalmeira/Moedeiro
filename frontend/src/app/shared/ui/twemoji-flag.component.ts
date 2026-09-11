import { ChangeDetectionStrategy, Component, input } from '@angular/core';

type TwemojiFlag = 'br' | 'us';

const FLAG_ASSETS: Record<TwemojiFlag, string> = {
  br: '/twemoji/1f1e7-1f1f7.svg',
  us: '/twemoji/1f1fa-1f1f8.svg',
};

@Component({
  selector: 'app-twemoji-flag',
  standalone: true,
  template: `<img [src]="source()" alt="" aria-hidden="true" draggable="false" />`,
  styles: `
    :host { display: inline-grid; place-items: center; width: 22px; height: 22px; line-height: 0; }
    img { display: block; width: 100%; height: 100%; object-fit: contain; user-select: none; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TwemojiFlagComponent {
  readonly country = input.required<TwemojiFlag>();

  source(): string {
    return FLAG_ASSETS[this.country()];
  }
}
