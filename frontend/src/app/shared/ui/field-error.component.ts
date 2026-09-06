import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-field-error',
  standalone: true,
  template: `@if (text()) { <small class="field-error" [class.field-error--visually-hidden]="visuallyHidden()" [id]="messageId()" role="alert">{{ text() }}</small> }`,
  styles: `
    :host { display: block; min-width: 0; }
    :host:empty { display: none; }
    .field-error--visually-hidden { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FieldErrorComponent {
  readonly text = input<string | null>(null);
  readonly messageId = input<string | null>(null);
  readonly visuallyHidden = input(false);
}
