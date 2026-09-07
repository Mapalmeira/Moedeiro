import { describe, expect, it } from 'vitest';
import { formatCurrencyAmount, formatCurrencyNumber, parseCurrencyAmount } from './currency-format';

describe('currency amount formatting', () => {
  const currency = { prefix: 'R$ ', suffix: null, decimal_places: 2 };

  it('converts comma and dot decimal input to integer minor units', () => {
    expect(parseCurrencyAmount('12,34', 2)).toBe(1234);
    expect(parseCurrencyAmount('12.34', 2)).toBe(1234);
  });

  it('rejects precision that the currency cannot represent', () => {
    expect(parseCurrencyAmount('12.345', 2)).toBeNull();
  });

  it('formats the numeric portion with the selected number format', () => {
    expect(formatCurrencyNumber(123456, 2, 'COMMA')).toBe('1.234,56');
    expect(formatCurrencyNumber(123456, 2, 'DOT')).toBe('1,234.56');
  });

  it('places a negative sign before the persisted currency prefix', () => {
    expect(formatCurrencyAmount(-12890, currency, 'COMMA')).toBe('−R$ 128,90');
  });
});
