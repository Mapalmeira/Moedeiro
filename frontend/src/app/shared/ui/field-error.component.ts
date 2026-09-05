import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-field-error',
  standalone: true,
  template: `@if (text()) { <small class="field-error" role="alert">{{ text() }}</small> }`,
  styles: `
    :host { display: block; min-width: 0; }
    :host:empty { display: none; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FieldErrorComponent {
  readonly text = input<string | null>(null);
}
