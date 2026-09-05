import { describe, expect, it } from 'vitest';
import { bestContrastingForeground } from './ledger-appearance';

describe('bestContrastingForeground', () => {
  it('uses white on a dark background', () => {
    const result = bestContrastingForeground('#172727');

    expect(result.foreground).toBe('#FFFFFF');
    expect(result.ratio).toBeGreaterThan(4.5);
  });

  it('uses black on a light background', () => {
    const result = bestContrastingForeground('#F7F7F7');

    expect(result.foreground).toBe('#000000');
    expect(result.ratio).toBeGreaterThan(4.5);
  });

  it('falls back to white background semantics for malformed colors', () => {
    expect(bestContrastingForeground('not-a-color').foreground).toBe('#000000');
  });
});
