import { ChangeDetectionStrategy, Component, effect, input, signal, untracked } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { I18nService } from '../../core/i18n/i18n.service';
import { inject } from '@angular/core';
import { DEFAULT_LEDGER_APPEARANCE, isHexColor } from './ledger-appearance';

@Component({
  selector: 'app-ledger-color-field',
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <section class="appearance-field">
      <span class="field-label">{{ i18n.t('ledgers.editor.color') }}</span>
      <div class="color-row">
        <input class="color-picker" type="color" [value]="color()" (input)="setColor($event)" [attr.aria-label]="i18n.t('ledgers.editor.color')" />
        <label class="field color-code-field"><input type="text" [formControl]="colorControl()" maxlength="7" autocomplete="off" aria-label="Hex" (input)="setColorText($event)" /></label>
      </div>
    </section>
  `,
  styles: `
    :host { display: block; min-width: 0; }
    .appearance-field { display: grid; gap: var(--field-gap); min-width: 0; }
    .field-label { font-size: var(--control-font-size); font-weight: 780; }
    .color-row { display: grid; grid-template-columns: 70px minmax(0, 1fr); gap: var(--space-3); }
    .color-picker { width: 70px; height: var(--control-height); padding: var(--space-1); border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-sm); background: var(--surface); }
    .color-picker::-webkit-color-swatch-wrapper { padding: 0; }
    .color-picker::-webkit-color-swatch, .color-picker::-moz-color-swatch { border: 0; border-radius: 3px; }
    .color-code-field { gap: 0; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerColorFieldComponent {
  readonly i18n = inject(I18nService);
  readonly colorControl = input.required<FormControl<string>>();
  readonly color = signal(DEFAULT_LEDGER_APPEARANCE.color);

  constructor() {
    effect((onCleanup) => {
      const control = this.colorControl();
      const sync = (value: string) => { if (isHexColor(value)) this.color.set(value); };
      untracked(() => sync(control.value));
      const subscription = control.valueChanges.subscribe(sync);
      onCleanup(() => subscription.unsubscribe());
    });
  }

  setColor(event: Event): void {
    const value = (event.target as HTMLInputElement).value.toUpperCase();
    this.colorControl().setValue(value);
    this.colorControl().markAsDirty();
    this.color.set(value);
  }

  setColorText(event: Event): void {
    const value = (event.target as HTMLInputElement).value.toUpperCase();
    this.colorControl().setValue(value);
    this.colorControl().markAsDirty();
    if (isHexColor(value)) this.color.set(value);
  }
}
