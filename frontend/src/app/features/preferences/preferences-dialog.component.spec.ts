import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../core/api/api-error';
import { I18nService } from '../../core/i18n/i18n.service';
import { UserPreferences } from '../../core/preferences/preferences.models';
import { PreferencesService } from '../../core/preferences/preferences.service';
import { ThemeService } from '../../core/theme/theme.service';
import { PreferencesDialogComponent } from './preferences-dialog.component';

describe('PreferencesDialogComponent', () => {
  const current = signal({ language: 'pt-BR' as const, theme: 'DARK' as const });
  const language = signal<'pt-BR' | 'en'>('pt-BR');
  const theme = signal<'light' | 'dark'>('dark');
  const preferences = {
    current: current.asReadonly(),
    get: vi.fn<() => Observable<UserPreferences>>(() => of(current())),
    save: vi.fn<() => Observable<UserPreferences>>(() => of({ language: 'en', theme: 'LIGHT' })),
  };
  const i18n = { language: language.asReadonly(), setLanguage: vi.fn((value: 'pt-BR' | 'en') => language.set(value)), t: vi.fn((key: string) => key) };
  const themeService = { theme: theme.asReadonly(), preview: vi.fn((value: 'light' | 'dark') => theme.set(value)), set: vi.fn((value: 'light' | 'dark') => theme.set(value)) };
  let fixture: ComponentFixture<PreferencesDialogComponent>;

  beforeEach(() => {
    vi.clearAllMocks();
    current.set({ language: 'pt-BR', theme: 'DARK' });
    language.set('pt-BR');
    theme.set('dark');
    preferences.get.mockImplementation(() => of(current()));
    preferences.save.mockImplementation(() => of({ language: 'en', theme: 'LIGHT' }));
    TestBed.configureTestingModule({
      imports: [PreferencesDialogComponent],
      providers: [
        { provide: PreferencesService, useValue: preferences },
        { provide: ThemeService, useValue: themeService },
        { provide: I18nService, useValue: i18n },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'save failed') } },
      ],
    });
    fixture = TestBed.createComponent(PreferencesDialogComponent);
    fixture.componentRef.setInput('open', true);
    fixture.detectChanges();
  });

  it('previews language and theme changes without persisting them', () => {
    fixture.componentInstance.setLanguage('en');
    fixture.componentInstance.setTheme('LIGHT');

    expect(i18n.setLanguage).toHaveBeenCalledWith('en');
    expect(themeService.preview).toHaveBeenCalledWith('light');
    expect(preferences.save).not.toHaveBeenCalled();
  });

  it('commits saved preferences and closes with the latest backend state', () => {
    const closed = vi.fn();
    fixture.componentInstance.close.subscribe(closed);
    fixture.componentInstance.form.setValue({ language: 'en', theme: 'LIGHT' });
    preferences.get.mockReturnValue(of({ language: 'en', theme: 'LIGHT' }));

    fixture.componentInstance.save();

    expect(preferences.save).toHaveBeenCalledWith({ language: 'en', theme: 'LIGHT' });
    expect(themeService.set).toHaveBeenCalledWith('light');
    expect(i18n.setLanguage).toHaveBeenCalledWith('en');
    expect(closed).toHaveBeenCalledOnce();
  });

  it('restores the last server state after a save failure', () => {
    preferences.save.mockReturnValue(throwError(() => new Error('offline')));
    fixture.componentInstance.setLanguage('en');
    fixture.componentInstance.setTheme('LIGHT');

    fixture.componentInstance.save();

    expect(fixture.componentInstance.form.getRawValue()).toEqual({ language: 'pt-BR', theme: 'DARK' });
    expect(themeService.set).toHaveBeenCalledWith('dark');
    expect(i18n.setLanguage).toHaveBeenCalledWith('pt-BR');
    expect(fixture.componentInstance.errorMessage()).toBe('save failed');
  });

  it('restores committed local values when refreshing on close fails', () => {
    const closed = vi.fn();
    fixture.componentInstance.close.subscribe(closed);
    fixture.componentInstance.setLanguage('en');
    fixture.componentInstance.setTheme('LIGHT');
    preferences.get.mockReturnValue(throwError(() => new Error('offline')));

    fixture.componentInstance.requestClose();

    expect(themeService.set).toHaveBeenCalledWith('dark');
    expect(i18n.setLanguage).toHaveBeenCalledWith('pt-BR');
    expect(closed).toHaveBeenCalledOnce();
  });
});
