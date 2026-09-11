export type PeriodMode = 'month' | 'range';

export interface TimestampRange {
  from: number;
  to: number;
}

interface DateInputRange {
  from: string;
  to: string;
}

interface ParsedMonth {
  year: number;
  month: number;
}

interface ParsedDateInput {
  year: number;
  month: number;
  day: number;
}

function pad(value: number, length = 2): string {
  return String(value).padStart(length, '0');
}

function parseMonth(value: string): ParsedMonth | null {
  const match = /^(\d{4})-(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  return month >= 1 && month <= 12 ? { year, month } : null;
}

function parseDateInput(value: string): ParsedDateInput | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  const date = localDate(year, month - 1, day);
  return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day
    ? { year, month, day }
    : null;
}

function localDate(year: number, monthIndex: number, day: number): Date {
  const date = new Date(0);
  date.setHours(0, 0, 0, 0);
  date.setFullYear(year, monthIndex, day);
  return date;
}

export function currentMonthValue(now = new Date()): string {
  return `${pad(now.getFullYear(), 4)}-${pad(now.getMonth() + 1)}`;
}

export function monthDateRange(monthValue: string): DateInputRange | null {
  const parsed = parseMonth(monthValue);
  if (!parsed) return null;
  const lastDay = localDate(parsed.year, parsed.month, 0).getDate();
  const prefix = `${pad(parsed.year, 4)}-${pad(parsed.month)}`;
  return { from: `${prefix}-01`, to: `${prefix}-${pad(lastDay)}` };
}

export function monthTimestampRange(monthValue: string): TimestampRange | null {
  const parsed = parseMonth(monthValue);
  if (!parsed) return null;
  return {
    from: Math.floor(localDate(parsed.year, parsed.month - 1, 1).getTime() / 1000),
    to: Math.floor(localDate(parsed.year, parsed.month, 1).getTime() / 1000),
  };
}

export function dateInputTimestampRange(fromValue: string, toValue: string): TimestampRange | null {
  const from = parseDateInput(fromValue);
  const to = parseDateInput(toValue);
  if (!from || !to) return null;
  const fromDate = localDate(from.year, from.month - 1, from.day);
  const toDate = localDate(to.year, to.month - 1, to.day + 1);
  const range = {
    from: Math.floor(fromDate.getTime() / 1000),
    to: Math.floor(toDate.getTime() / 1000),
  };
  return range.from < range.to ? range : null;
}

export function monthForDateRange(from: string, to: string): string | null {
  const month = from.slice(0, 7);
  const range = monthDateRange(month);
  return range?.from === from && range.to === to ? month : null;
}
