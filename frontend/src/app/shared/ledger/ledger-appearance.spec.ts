import { describe, expect, it } from 'vitest';
import { bestContrastingForeground } from './ledger-appearance';

describe('bestContrastingForeground', () => {
  it('uses white on a dark background', () => {
    expect(bestContrastingForeground('#172727')).toBe('#FFFFFF');
  });

  it('uses black on a light background', () => {
    expect(bestContrastingForeground('#F7F7F7')).toBe('#000000');
  });

  it('falls back to white background semantics for malformed colors', () => {
    expect(bestContrastingForeground('not-a-color')).toBe('#000000');
  });
});
