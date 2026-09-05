const UNICODE_ICON_PREFIX = 'unicode:';
const LUCIDE_ICON_PREFIX = 'lucide:';

export function encodeUnicodeLedgerIcon(value: string): string {
  return `${UNICODE_ICON_PREFIX}${value}`;
}

export function encodeLucideLedgerIcon(value: string): string {
  return `${LUCIDE_ICON_PREFIX}${value}`;
}

export function isEncodedUnicodeLedgerIcon(value: string): boolean {
  return value.startsWith(UNICODE_ICON_PREFIX);
}

export function isEncodedLucideLedgerIcon(value: string): boolean {
  return value.startsWith(LUCIDE_ICON_PREFIX);
}

export function decodeUnicodeLedgerIcon(value: string): string {
  return isEncodedUnicodeLedgerIcon(value) ? value.slice(UNICODE_ICON_PREFIX.length) : '';
}

export function decodeLucideLedgerIcon(value: string): string {
  return isEncodedLucideLedgerIcon(value) ? value.slice(LUCIDE_ICON_PREFIX.length) : '';
}
