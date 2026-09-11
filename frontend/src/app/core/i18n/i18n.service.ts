import { DOCUMENT } from '@angular/common';
import { inject, Injectable, signal } from '@angular/core';
import { en } from './translations/en';
import { ptBR } from './translations/pt-br';
import type { TranslationKey } from './translations/pt-br';

export type AppLanguage = 'pt-BR' | 'en';
export type { TranslationKey } from './translations/pt-br';

const dictionaries: Record<AppLanguage, Record<TranslationKey, string>> = { 'pt-BR': ptBR, en };

@Injectable({ providedIn: 'root' })
export class I18nService {
  private readonly document = inject(DOCUMENT);
  private readonly storageKey = 'moedeiro-language';
  readonly language = signal<AppLanguage>(this.initialLanguage());

  constructor() {
    this.applyDocumentLanguage(this.language());
  }

  t(key: TranslationKey, params?: Record<string, string | number>): string {
    let value = dictionaries[this.language()][key] ?? ptBR[key];
    if (!params) return value;
    for (const [name, replacement] of Object.entries(params)) {
      value = value.replaceAll(`{${name}}`, String(replacement));
    }
    return value;
  }

  setLanguage(language: AppLanguage): void {
    if (language === this.language()) return;
    this.language.set(language);
    this.applyDocumentLanguage(language);
    try {
      localStorage.setItem(this.storageKey, language);
    } catch {
      // Language still changes for the current page when storage is unavailable.
    }
  }

  private initialLanguage(): AppLanguage {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (stored === 'pt-BR' || stored === 'en') return stored;
    } catch {
      // Fall back to the browser language.
    }
    const browserLanguages = typeof navigator !== 'undefined'
      ? [...navigator.languages, navigator.language]
      : ['pt-BR'];
    for (const language of browserLanguages) {
      const normalized = language.toLowerCase();
      if (normalized.startsWith('pt')) return 'pt-BR';
      if (normalized.startsWith('en')) return 'en';
    }
    return 'en';
  }

  private applyDocumentLanguage(language: AppLanguage): void {
    this.document.documentElement.lang = language === 'en' ? 'en' : 'pt-BR';
  }
}
