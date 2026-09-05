import { inject, Injectable } from '@angular/core';
import { I18nService } from '../i18n/i18n.service';
import { ThemeService } from '../theme/theme.service';
import type { DateFormat, NumberFormat, TimeFormat, UserPreferences } from './preferences.models';

/**
 * Builds a concrete initial preference set from the browser environment.
 *
 * Language and theme use the values currently selected in the public UI.
 * ThemeService defaults to LIGHT when the browser has no previous Moedeiro
 * choice, so the operating-system theme is never inferred; an explicit theme
 * choice made before account creation is preserved. Date, time, number
 * formatting and time zone are inferred from Intl.
 */
@Injectable({ providedIn: 'root' })
export class PreferenceDefaultsService {
  private readonly i18n = inject(I18nService);
  private readonly theme = inject(ThemeService);

  infer(): UserPreferences {
    const locale = this.browserLocale();

    return {
      language: this.i18n.language(),
      date_format: this.inferDateFormat(locale),
      time_format: this.inferTimeFormat(locale),
      number_format: this.inferNumberFormat(locale),
      theme: this.theme.theme() === 'dark' ? 'DARK' : 'LIGHT',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    };
  }

  private browserLocale(): string {
    return navigator.languages[0] ?? navigator.language;
  }

  private inferDateFormat(locale: string): DateFormat {
    const parts = new Intl.DateTimeFormat(locale, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(new Date(2006, 10, 22));

    const order = parts
      .filter((part) => part.type === 'day' || part.type === 'month' || part.type === 'year')
      .map((part) => part.type)
      .join('-');

    if (order === 'day-month-year') return 'DMY';
    if (order === 'year-month-day') return 'YMD';
    return 'MDY';
  }

  private inferTimeFormat(locale: string): TimeFormat {
    const options = new Intl.DateTimeFormat(locale, { hour: 'numeric' }).resolvedOptions();
    return options.hour12 ? 'H12' : 'H24';
  }

  private inferNumberFormat(locale: string): NumberFormat {
    const formatted = new Intl.NumberFormat(locale, { useGrouping: false }).format(1.1);
    return formatted.includes(',') ? 'COMMA' : 'DOT';
  }
}
