import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import type { LedgerCurrency } from '../../core/ledgers/ledger-entities.models';
import { currencyAmountInput, formatCurrencyNumber, parseCurrencyAmount } from '../../core/ledgers/currency-format';

@Component({
  selector: 'app-currency-amount-input',
  standalone: true,
  template: `
    <div class="currency-amount" [class.currency-amount--disabled]="disabled()">
      @if (currency()?.prefix; as prefix) { <span class="currency-amount__affix">{{ prefix }}</span> }
      <input type="text" inputmode="numeric" autocomplete="off" [disabled]="disabled()"
        [attr.aria-label]="ariaLabel()" [attr.aria-required]="required() ? 'true' : null"
        [value]="displayValue()" (input)="onInput($event)" />
      @if (currency()?.suffix; as suffix) { <span class="currency-amount__affix">{{ suffix }}</span> }
    </div>
  `,
  styles: `
    :host { display: block; min-width: 0; }
    .currency-amount {
      box-sizing: border-box;
      width: 100%;
      height: var(--control-height);
      min-height: var(--control-height);
      display: flex;
      align-items: center;
      gap: var(--space-2);
      padding: 0 var(--control-padding-inline);
      border: var(--border-width) solid var(--line-strong);
      border-radius: var(--radius-sm);
      background: var(--surface);
      color: var(--text);
      transition: box-shadow var(--motion-focus) ease, border-color var(--motion-focus) ease, background var(--motion-focus) ease;
    }
    .currency-amount:focus-within {
      border-color: var(--ui-accent-strong);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--ui-accent) 32%, transparent);
    }
    .currency-amount--disabled { background: var(--surface-muted); color: var(--text-muted); }
    .currency-amount__affix { flex: 0 0 auto; font-size: var(--control-font-size); font-weight: 650; white-space: pre; }
    input {
      min-width: 0;
      width: 100%;
      height: 100%;
      padding: 0;
      border: 0;
      outline: 0;
      background: transparent;
      color: inherit;
      font: inherit;
      font-size: var(--control-font-size);
      font-weight: 500;
      line-height: var(--control-line-height);
      font-variant-numeric: tabular-nums;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CurrencyAmountInputComponent {
  readonly currency = input<LedgerCurrency | null>(null);
  readonly value = input('');
  readonly ariaLabel = input('');
  readonly required = input(false);
  readonly disabled = input(false);
  readonly valueChange = output<string>();

  readonly displayValue = computed(() => {
    const raw = this.value();
    if (!raw) return '';
    const currency = this.currency();
    if (!currency) return raw.replace(/[^\d.,]/g, '');
    const minor = parseCurrencyAmount(raw, currency.decimal_places);
    return minor === null ? '' : formatCurrencyNumber(minor, currency.decimal_places);
  });

  onInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    const currency = this.currency();
    const precision = currency?.decimal_places ?? 2;
    const digits = input.value.replace(/\D/g, '').replace(/^0+(?=\d)/, '');
    if (!digits || /^0+$/.test(digits)) {
      input.value = '';
      this.valueChange.emit('');
      return;
    }

    const padded = precision > 0 ? digits.padStart(precision + 1, '0') : digits;
    const canonical = precision > 0
      ? `${padded.slice(0, -precision)}.${padded.slice(-precision)}`
      : padded;
    const minor = parseCurrencyAmount(canonical, precision);
    if (minor === null || minor <= 0) {
      input.value = this.displayValue();
      return;
    }

    input.value = formatCurrencyNumber(minor, precision);
    this.valueChange.emit(currencyAmountInput(minor, precision));
  }
}
