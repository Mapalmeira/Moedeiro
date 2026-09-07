import type { NumberFormat } from '../preferences/preferences.models';

export interface CurrencyFormatDefinition {
  prefix: string | null;
  suffix: string | null;
  decimal_places: number;
}

function clampedPrecision(decimalPlaces: number): number {
  return Number.isInteger(decimalPlaces) ? Math.max(0, Math.min(20, decimalPlaces)) : 2;
}

/** Prefix/suffix whitespace is part of the currency's persisted format. */
export function formatCurrencyPreview(currency: CurrencyFormatDefinition, format: NumberFormat): string {
  return formatCurrencyAmount(10 * (10 ** clampedPrecision(currency.decimal_places)), currency, format);
}

export function formatCurrencyNumber(value: number, decimalPlaces: number, format: NumberFormat): string {
  const precision = clampedPrecision(decimalPlaces);
  const divisor = 10 ** precision;
  return new Intl.NumberFormat(format === 'COMMA' ? 'de-DE' : 'en-US', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  }).format(Math.abs(value) / divisor);
}

export function formatCurrencyAmount(value: number, currency: CurrencyFormatDefinition, format: NumberFormat): string {
  const negative = value < 0;
  const number = formatCurrencyNumber(value, currency.decimal_places, format);
  return `${negative ? '−' : ''}${currency.prefix ?? ''}${number}${currency.suffix ?? ''}`;
}

/**
 * Converts a user-entered decimal amount into the integer minor-unit contract
 * used by the ledger API. Both comma and dot are accepted as decimal marks.
 */
export function parseCurrencyAmount(rawValue: string, decimalPlaces: number): number | null {
  const precision = clampedPrecision(decimalPlaces);
  const normalized = rawValue.trim().replace(',', '.');
  if (!/^\d+(?:\.\d+)?$/.test(normalized)) return null;
  const [whole, fraction = ''] = normalized.split('.');
  if (fraction.length > precision) return null;
  try {
    const scale = 10n ** BigInt(precision);
    const minor = BigInt(whole) * scale + BigInt((fraction + '0'.repeat(precision)).slice(0, precision) || '0');
    if (minor > BigInt(Number.MAX_SAFE_INTEGER)) return null;
    return Number(minor);
  } catch {
    return null;
  }
}

export function currencyAmountInput(value: number, decimalPlaces: number): string {
  const precision = clampedPrecision(decimalPlaces);
  const absolute = Math.abs(value);
  if (precision === 0) return String(absolute);
  const scale = 10 ** precision;
  const whole = Math.floor(absolute / scale);
  const fraction = String(absolute % scale).padStart(precision, '0');
  return `${whole}.${fraction}`;
}
