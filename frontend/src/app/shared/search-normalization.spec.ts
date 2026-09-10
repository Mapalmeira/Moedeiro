import { describe, expect, it } from 'vitest';
import { normalizeSearchText } from './search-normalization';

describe('normalizeSearchText', () => {
  it('normalizes case and diacritics', () => {
    expect(normalizeSearchText('Café À LA CARTE')).toBe('cafe a la carte');
  });
});
