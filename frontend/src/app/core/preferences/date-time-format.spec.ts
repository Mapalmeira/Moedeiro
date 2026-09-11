import { describe, expect, it } from 'vitest';
import { formatEventDate, formatEventTime, nextDateInput, zonedDateInput, zonedDateTimeToEpochSeconds, zonedTimeInput } from './date-time-format';

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

  it('uses the browser locale for date and time presentation', () => {
    const timestamp = Date.parse('2026-09-07T18:50:07Z') / 1000;
    const date = new Date(timestamp * 1000);
    const expectedDate = new Intl.DateTimeFormat(undefined, {
      timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit',
    }).format(date);
    const expectedTime = new Intl.DateTimeFormat(undefined, {
      timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', second: '2-digit',
    }).format(date);

    expect(formatEventDate(timestamp, 'America/Sao_Paulo')).toBe(expectedDate);
    expect(formatEventTime(timestamp, 'America/Sao_Paulo')).toBe(expectedTime);
  });

  it('advances real calendar dates and rejects impossible ones', () => {
    expect(nextDateInput('2026-09-30')).toBe('2026-10-01');
    expect(nextDateInput('2024-02-29')).toBe('2024-03-01');
    expect(nextDateInput('2026-02-29')).toBeNull();
    expect(nextDateInput('2026-02-31')).toBeNull();
  });
});
