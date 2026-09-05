import type { AppLanguage } from '../i18n/i18n.service';

export type DateFormat = 'DMY' | 'MDY' | 'YMD';
export type TimeFormat = 'H12' | 'H24';
export type NumberFormat = 'COMMA' | 'DOT';
export type BackendTheme = 'LIGHT' | 'DARK';

export interface UserPreferences {
  language: AppLanguage;
  date_format: DateFormat;
  time_format: TimeFormat;
  number_format: NumberFormat;
  theme: BackendTheme;
  timezone: string;
}

