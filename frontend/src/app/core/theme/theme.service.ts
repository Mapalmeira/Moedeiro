import { DOCUMENT } from '@angular/common';
import { inject, Injectable, signal } from '@angular/core';
import type { BackendTheme } from '../preferences/preferences.models';

export type UiTheme = 'light' | 'dark';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);
  private readonly storageKey = 'moedeiro-ui-theme';
  readonly theme = signal<UiTheme>(this.initialTheme());

  constructor() {
    this.apply(this.theme());
  }

  toggle(): void {
    this.set(this.theme() === 'dark' ? 'light' : 'dark');
  }

  set(theme: UiTheme): void {
    this.preview(theme);
    try {
      localStorage.setItem(this.storageKey, theme);
    } catch {
      // The selected theme still applies to the current page.
    }
  }

  preview(theme: UiTheme): void {
    this.theme.set(theme);
    this.apply(theme);
  }

  applyBackendPreference(value: BackendTheme): void {
    this.set(value === 'DARK' ? 'dark' : 'light');
  }

  private initialTheme(): UiTheme {
    try {
      const saved = localStorage.getItem(this.storageKey);
      if (saved === 'light' || saved === 'dark') return saved;
    } catch {
      // If storage is unavailable, use the application's default theme.
    }
    return 'light';
  }

  private apply(theme: UiTheme): void {
    this.document.documentElement.dataset['theme'] = theme;
    this.document.documentElement.style.colorScheme = theme;
  }
}
