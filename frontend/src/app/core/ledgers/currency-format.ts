import { NumberFormat } from '../preferences/preferences.models';

/** Prefix/suffix whitespace is part of the currency's persisted format. */
export function formatCurrencyPreview(currency: { prefix: string | null; suffix: string | null; decimal_places: number }, format: NumberFormat): string {
  const precision = Number.isInteger(currency.decimal_places) ? Math.max(0, Math.min(20, currency.decimal_places)) : 2;
  const number = new Intl.NumberFormat(format === 'COMMA' ? 'de-DE' : 'en-US', {
    minimumFractionDigits: precision, maximumFractionDigits: precision,
  }).format(10);
  return `${currency.prefix ?? ''}${number}${currency.suffix ?? ''}`;
}
