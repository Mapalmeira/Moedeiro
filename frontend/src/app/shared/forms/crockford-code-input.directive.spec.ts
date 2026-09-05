import { describe, expect, it } from 'vitest';
import { CROCKFORD_CODE_PATTERN, formatCrockfordCode, normalizeCrockfordCode } from './crockford-code-input.directive';

describe('Crockford code helpers', () => {
  it('normalizes case, separators and length', () => {
    expect(normalizeCrockfordCode('abcd-efgh-jkmn-pqrst-extra')).toBe('ABCDEFGHJKMNPQRS');
  });

  it('formats normalized values in groups of four', () => {
    expect(formatCrockfordCode('abcdefghjkmnpqrs')).toBe('ABCD-EFGH-JKMN-PQRS');
  });

  it('matches only a complete 16-character Crockford code', () => {
    expect(CROCKFORD_CODE_PATTERN.test('ABCDEFGHJKMNPQRS')).toBe(true);
    expect(CROCKFORD_CODE_PATTERN.test('ABCDEFGHJKMNPQR')).toBe(false);
    expect(CROCKFORD_CODE_PATTERN.test('ABCDEFGHJKMNPQRI')).toBe(false);
  });
});
