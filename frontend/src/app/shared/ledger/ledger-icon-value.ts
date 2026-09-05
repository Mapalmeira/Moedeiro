const UNICODE_ICON_PREFIX = 'unicode:';

export function encodeUnicodeLedgerIcon(value: string): string {
  return `${UNICODE_ICON_PREFIX}${value}`;
}

export function isEncodedUnicodeLedgerIcon(value: string): boolean {
  return value.startsWith(UNICODE_ICON_PREFIX);
}

export function decodeUnicodeLedgerIcon(value: string): string {
  return isEncodedUnicodeLedgerIcon(value) ? value.slice(UNICODE_ICON_PREFIX.length) : value;
}
