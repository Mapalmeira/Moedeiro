import { inject, Injectable } from '@angular/core';
import { I18nService } from '../i18n/i18n.service';
import { ThemeService } from '../theme/theme.service';
import type { UserPreferences } from './preferences.models';

/** Builds the persisted preferences that are not owned by the browser/OS locale. */
@Injectable({ providedIn: 'root' })
export class PreferenceDefaultsService {
  private readonly i18n = inject(I18nService);
  private readonly theme = inject(ThemeService);

  infer(): UserPreferences {
    return {
      language: this.i18n.language(),
      theme: this.theme.theme() === 'dark' ? 'DARK' : 'LIGHT',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    };
  }
}
