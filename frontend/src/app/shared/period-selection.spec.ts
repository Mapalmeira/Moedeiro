import { currentMonthValue, dateInputTimestampRange, monthDateRange, monthForDateRange, monthTimestampRange } from './period-selection';

describe('period selection', () => {
  it('builds month date ranges including leap years', () => {
    expect(monthDateRange('2028-02')).toEqual({ from: '2028-02-01', to: '2028-02-29' });
    expect(monthForDateRange('2028-02-01', '2028-02-29')).toBe('2028-02');
  });

  it('rejects invalid date inputs', () => {
    expect(dateInputTimestampRange('2026-02-01', '2026-02-31')).toBeNull();
    expect(monthTimestampRange('2026-13')).toBeNull();
  });

  it('uses local calendar boundaries for timestamp ranges', () => {
    const range = dateInputTimestampRange('2026-09-10', '2026-09-10');
    expect(range).not.toBeNull();
    expect((range!.to - range!.from)).toBeGreaterThan(0);
  });

  it('formats the current month from a Date', () => {
    expect(currentMonthValue(new Date(2026, 8, 11))).toBe('2026-09');
  });
});
