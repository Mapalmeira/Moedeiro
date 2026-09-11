import type { AppLanguage } from '../i18n/i18n.service';

export type BackendTheme = 'LIGHT' | 'DARK';

export interface UserPreferences {
  language: AppLanguage;
  theme: BackendTheme;
}
