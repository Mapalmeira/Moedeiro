import { describe, expect, it } from 'vitest';
import { DEFAULT_CATEGORY_APPEARANCE, DEFAULT_CURRENCY_APPEARANCE, HEX_COLOR_PATTERN, bestContrastingForeground, isHexColor } from './ledger-appearance';

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


describe('ledger appearance defaults', () => {
  it('shares one hex color contract between validation helpers and forms', () => {
    expect(isHexColor('#21E683')).toBe(true);
    expect(HEX_COLOR_PATTERN.test('#FFD51A')).toBe(true);
    expect(isHexColor('#12345')).toBe(false);
  });

  it('keeps the domain defaults centralized', () => {
    expect(DEFAULT_CURRENCY_APPEARANCE).toEqual({ icon: 'lucide:Coins', color: '#FFD51A' });
    expect(DEFAULT_CATEGORY_APPEARANCE).toEqual({ icon: 'lucide:Folder', color: '#488DFC' });
  });
});
