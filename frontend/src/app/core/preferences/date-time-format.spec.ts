import { describe, expect, it } from 'vitest';
import { formatEventDate, formatEventTime, zonedDateInput, zonedDateTimeToEpochSeconds, zonedTimeInput } from './date-time-format';

describe('ledger date and time formatting', () => {
  it('converts a wall clock time with seconds in the preference time zone to epoch seconds', () => {
    expect(zonedDateTimeToEpochSeconds('2026-09-07', '15:50:07', 'America/Sao_Paulo')).toBe(Date.parse('2026-09-07T18:50:07Z') / 1000);
  });

  it('keeps accepting minute-only wall clock values as zero seconds', () => {
    expect(zonedDateTimeToEpochSeconds('2026-09-07', '15:50', 'America/Sao_Paulo')).toBe(Date.parse('2026-09-07T18:50:00Z') / 1000);
  });

  it('round-trips date and time inputs through the configured time zone including seconds', () => {
    const timestamp = Date.parse('2026-09-07T18:50:07Z') / 1000;
    expect(zonedDateInput(timestamp, 'America/Sao_Paulo')).toBe('2026-09-07');
    expect(zonedTimeInput(timestamp, 'America/Sao_Paulo')).toBe('15:50:07');
  });

  it('honors the selected date and time presentation formats including seconds', () => {
    const timestamp = Date.parse('2026-09-07T18:50:07Z') / 1000;
    expect(formatEventDate(timestamp, 'America/Sao_Paulo', 'DMY')).toBe('07/09/2026');
    expect(formatEventTime(timestamp, 'America/Sao_Paulo', 'H24')).toBe('15:50:07');
    expect(formatEventTime(timestamp, 'America/Sao_Paulo', 'H12')).toBe('03:50:07 PM');
  });
});
