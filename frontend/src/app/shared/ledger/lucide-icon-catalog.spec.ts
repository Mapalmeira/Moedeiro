import { describe, expect, it } from 'vitest';
import { LUCIDE_ICON_CATALOG, resolveLucideIcon, resolveLucideIconLabel } from './lucide-icon-catalog';

describe('lucide icon catalog', () => {
  it('exposes unique persisted ids', () => {
    const ids = LUCIDE_ICON_CATALOG.map(entry => entry.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('resolves a canonical icon id and its human-readable label', () => {
    expect(resolveLucideIcon('Wallet')).not.toBeNull();
    expect(resolveLucideIconLabel('Wallet')).toBe('Wallet');
  });

  it('does not resolve unknown persisted ids', () => {
    expect(resolveLucideIcon('DefinitelyNotAnIcon')).toBeNull();
    expect(resolveLucideIconLabel('DefinitelyNotAnIcon')).toBe('');
  });
});
