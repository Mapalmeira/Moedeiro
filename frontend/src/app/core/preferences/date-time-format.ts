import type { DateFormat, TimeFormat } from './preferences.models';

const zonedPartsFormatters = new Map<string, Intl.DateTimeFormat>();
const eventTimeFormatters = new Map<string, Intl.DateTimeFormat>();

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
  const key = `${timezone}|${format}`;
  let formatter = eventTimeFormatters.get(key);
  if (!formatter) {
    formatter = new Intl.DateTimeFormat(format === 'H12' ? 'en-US' : 'pt-BR', {
      timeZone: timezone,
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: format === 'H12',
    });
    eventTimeFormatters.set(key, formatter);
  }
  return formatter.format(new Date(timestampSeconds * 1000));
}
