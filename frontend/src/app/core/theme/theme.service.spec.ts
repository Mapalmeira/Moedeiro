import { DOCUMENT } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
    document.documentElement.style.colorScheme = '';
    TestBed.configureTestingModule({ providers: [{ provide: DOCUMENT, useValue: document }] });
  });

  it('restores and applies a persisted theme', () => {
    localStorage.setItem('moedeiro-ui-theme', 'dark');
    const service = TestBed.inject(ThemeService);

    expect(service.theme()).toBe('dark');
    expect(document.documentElement.dataset['theme']).toBe('dark');
    expect(document.documentElement.style.colorScheme).toBe('dark');
  });

  it('toggles and persists the selected theme', () => {
    const service = TestBed.inject(ThemeService);
    service.toggle();

    expect(service.theme()).toBe('dark');
    expect(localStorage.getItem('moedeiro-ui-theme')).toBe('dark');
    expect(document.documentElement.dataset['theme']).toBe('dark');
  });

  it('previews without persisting and maps backend preferences', () => {
    const service = TestBed.inject(ThemeService);
    service.preview('dark');
    expect(localStorage.getItem('moedeiro-ui-theme')).toBeNull();

    service.applyBackendPreference('LIGHT');
    expect(service.theme()).toBe('light');
    expect(localStorage.getItem('moedeiro-ui-theme')).toBe('light');
  });

  it('still applies the theme when browser storage is unavailable', () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('disabled'); });
    const service = TestBed.inject(ThemeService);

    service.set('dark');

    expect(service.theme()).toBe('dark');
    expect(document.documentElement.dataset['theme']).toBe('dark');
    setItem.mockRestore();
  });
});
