import type { DateFormat, TimeFormat } from './preferences.models';

const zonedPartsFormatters = new Map<string, Intl.DateTimeFormat>();

interface ZonedDateTimeParts {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  second: number;
}

function partsAt(timestampMs: number, timezone: string): ZonedDateTimeParts {
  let formatter = zonedPartsFormatters.get(timezone);
  if (!formatter) {
    formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: timezone,
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
    });
    zonedPartsFormatters.set(timezone, formatter);
  }
  const parts = formatter.formatToParts(new Date(timestampMs));
  const values = Object.fromEntries(parts.filter(part => part.type !== 'literal').map(part => [part.type, part.value]));
  return {
    year: Number(values['year']), month: Number(values['month']), day: Number(values['day']),
    hour: Number(values['hour']), minute: Number(values['minute']), second: Number(values['second']),
  };
}

export function zonedDateTimeToEpochSeconds(date: string, time: string, timezone: string): number | null {
  const dateMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  const timeMatch = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(time);
  if (!dateMatch || !timeMatch) return null;
  const desired = {
    year: Number(dateMatch[1]), month: Number(dateMatch[2]), day: Number(dateMatch[3]),
    hour: Number(timeMatch[1]), minute: Number(timeMatch[2]), second: Number(timeMatch[3] ?? 0),
  };
  if (desired.month < 1 || desired.month > 12 || desired.day < 1 || desired.day > 31 || desired.hour > 23 || desired.minute > 59 || desired.second > 59) return null;
  const desiredAsUtc = Date.UTC(desired.year, desired.month - 1, desired.day, desired.hour, desired.minute, desired.second);
  let guess = desiredAsUtc;
  for (let index = 0; index < 3; index += 1) {
    const current = partsAt(guess, timezone);
    const currentAsUtc = Date.UTC(current.year, current.month - 1, current.day, current.hour, current.minute, current.second);
    const difference = desiredAsUtc - currentAsUtc;
    if (difference === 0) break;
    guess += difference;
  }
  const resolved = partsAt(guess, timezone);
  if (Object.entries(desired).some(([key, value]) => resolved[key as keyof ZonedDateTimeParts] !== value)) return null;
  return Math.floor(guess / 1000);
}

export function zonedDateInput(timestampSeconds: number, timezone: string): string {
  const parts = partsAt(timestampSeconds * 1000, timezone);
  return `${String(parts.year).padStart(4, '0')}-${String(parts.month).padStart(2, '0')}-${String(parts.day).padStart(2, '0')}`;
}

export function zonedTimeInput(timestampSeconds: number, timezone: string): string {
  const parts = partsAt(timestampSeconds * 1000, timezone);
  return `${String(parts.hour).padStart(2, '0')}:${String(parts.minute).padStart(2, '0')}:${String(parts.second).padStart(2, '0')}`;
}

/** Formats an ISO calendar date for an editable field without relying on the browser locale. */
export function formatDateInput(value: string, format: DateFormat): string {
  const parts = dateParts(value);
  if (!parts) return '';
  const { year, month, day } = parts;
  if (format === 'MDY') return `${month}/${day}/${year}`;
  if (format === 'YMD') return `${year}/${month}/${day}`;
  return `${day}/${month}/${year}`;
}

/** Parses the displayed date field value to the ISO value used by forms and the API. */
export function parseDateInput(value: string, format: DateFormat): string | null {
  const match = /^(\d{1,4})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{1,4})$/.exec(value.trim());
  if (!match) return null;
  const [first, second, third] = match.slice(1).map(Number);
  const parts = format === 'MDY'
    ? { year: third, month: first, day: second }
    : format === 'YMD'
      ? { year: first, month: second, day: third }
      : { year: third, month: second, day: first };
  if (parts.year < 1 || parts.year > 9999 || parts.month < 1 || parts.month > 12 || parts.day < 1 || parts.day > 31) return null;
  const date = new Date(0);
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCFullYear(parts.year, parts.month - 1, parts.day);
  if (date.getUTCFullYear() !== parts.year || date.getUTCMonth() !== parts.month - 1 || date.getUTCDate() !== parts.day) return null;
  return `${String(parts.year).padStart(4, '0')}-${String(parts.month).padStart(2, '0')}-${String(parts.day).padStart(2, '0')}`;
}

/** Formats an ISO clock time for an editable field according to the selected clock preference. */
export function formatTimeInput(value: string, format: TimeFormat): string {
  const parts = timeParts(value);
  if (!parts) return '';
  const seconds = parts.second === 0 ? '' : `:${String(parts.second).padStart(2, '0')}`;
  if (format === 'H24') return `${String(parts.hour).padStart(2, '0')}:${String(parts.minute).padStart(2, '0')}${seconds}`;
  const period = parts.hour >= 12 ? 'PM' : 'AM';
  const hour = parts.hour % 12 || 12;
  return `${String(hour).padStart(2, '0')}:${String(parts.minute).padStart(2, '0')}${seconds} ${period}`;
}

/** Parses the displayed clock field value to the ISO time used by forms and the API. */
export function parseTimeInput(value: string, format: TimeFormat): string | null {
  const match = format === 'H12'
    ? /^(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm)$/i.exec(value.trim())
    : /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(value.trim());
  if (!match) return null;
  let hour = Number(match[1]);
  const minute = Number(match[2]);
  const second = Number(match[3] ?? 0);
  if (format === 'H12') {
    if (hour < 1 || hour > 12) return null;
    const period = match[4]!.toUpperCase();
    hour = hour % 12 + (period === 'PM' ? 12 : 0);
  } else if (hour > 23) return null;
  if (minute > 59 || second > 59) return null;
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:${String(second).padStart(2, '0')}`;
}

function dateParts(value: string): { year: string; month: string; day: string } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  return { year: match[1], month: match[2], day: match[3] };
}

function timeParts(value: string): { hour: number; minute: number; second: number } | null {
  const match = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value);
  if (!match) return null;
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  const second = Number(match[3] ?? 0);
  if (hour > 23 || minute > 59 || second > 59) return null;
  return { hour, minute, second };
}

/** Returns the following calendar date without normalizing impossible input dates. */
export function nextDateInput(value: string): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(0);
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCFullYear(year, month - 1, day);
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
  date.setUTCDate(date.getUTCDate() + 1);
  return `${String(date.getUTCFullYear()).padStart(4, '0')}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`;
}

export function formatEventDate(timestampSeconds: number, timezone: string, format: DateFormat): string {
  const parts = partsAt(timestampSeconds * 1000, timezone);
  const day = String(parts.day).padStart(2, '0');
  const month = String(parts.month).padStart(2, '0');
  const year = String(parts.year).padStart(4, '0');
  if (format === 'MDY') return `${month}/${day}/${year}`;
  if (format === 'YMD') return `${year}/${month}/${day}`;
  return `${day}/${month}/${year}`;
}

export function formatEventTime(timestampSeconds: number, timezone: string, format: TimeFormat): string {
  const parts = partsAt(timestampSeconds * 1000, timezone);
  const minute = String(parts.minute).padStart(2, '0');
  const second = String(parts.second).padStart(2, '0');
  if (format === 'H24') return `${String(parts.hour).padStart(2, '0')}:${minute}:${second}`;
  const period = parts.hour >= 12 ? 'PM' : 'AM';
  const hour = parts.hour % 12 || 12;
  return `${String(hour).padStart(2, '0')}:${minute}:${second} ${period}`;
}
