import { describe, expect, it } from 'vitest';
import {
  decodeLucideLedgerIcon,
  decodeUnicodeLedgerIcon,
  encodeLucideLedgerIcon,
  encodeUnicodeLedgerIcon,
  isEncodedLucideLedgerIcon,
  isEncodedUnicodeLedgerIcon,
} from './ledger-icon-value';

describe('ledger icon values', () => {
  it('encodes and decodes unicode icons without ambiguity', () => {
    const encoded = encodeUnicodeLedgerIcon('R$');

    expect(encoded).toBe('unicode:R$');
    expect(isEncodedUnicodeLedgerIcon(encoded)).toBe(true);
    expect(isEncodedLucideLedgerIcon(encoded)).toBe(false);
    expect(decodeUnicodeLedgerIcon(encoded)).toBe('R$');
    expect(decodeLucideLedgerIcon(encoded)).toBe('');
  });

  it('encodes and decodes Lucide icons with an explicit prefix', () => {
    const encoded = encodeLucideLedgerIcon('WalletCards');

    expect(encoded).toBe('lucide:WalletCards');
    expect(isEncodedLucideLedgerIcon(encoded)).toBe(true);
    expect(isEncodedUnicodeLedgerIcon(encoded)).toBe(false);
    expect(decodeLucideLedgerIcon(encoded)).toBe('WalletCards');
    expect(decodeUnicodeLedgerIcon(encoded)).toBe('');
  });

  it('does not treat legacy bare values as encoded icons', () => {
    expect(isEncodedLucideLedgerIcon('WalletCards')).toBe(false);
    expect(isEncodedUnicodeLedgerIcon('💰')).toBe(false);
    expect(decodeLucideLedgerIcon('WalletCards')).toBe('');
    expect(decodeUnicodeLedgerIcon('💰')).toBe('');
  });
});
