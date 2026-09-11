import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nService } from './i18n.service';

describe('I18nService', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('uses the persisted language and exposes the current PT-BR copy', () => {
    localStorage.setItem('moedeiro-language', 'pt-BR');
    const service = TestBed.inject(I18nService);

    expect(service.language()).toBe('pt-BR');
    expect(service.t('ledgers.editor.preview')).toBe('Pré-visualização');
    expect(service.t('shell.logout')).toBe('Sair da conta');
    expect(document.documentElement.lang).toBe('pt-BR');
  });

  it('uses the first supported language from the browser preference list', () => {
    const languages = vi.spyOn(navigator, 'languages', 'get').mockReturnValue(['es-ES', 'pt-BR', 'en-US']);
    const language = vi.spyOn(navigator, 'language', 'get').mockReturnValue('es-ES');

    const service = TestBed.inject(I18nService);

    expect(service.language()).toBe('pt-BR');
    languages.mockRestore();
    language.mockRestore();
  });

  it('persists language changes and updates the document language', () => {
    localStorage.setItem('moedeiro-language', 'pt-BR');
    const service = TestBed.inject(I18nService);

    service.setLanguage('en');

    expect(service.t('ledgers.editor.preview')).toBe('Preview');
    expect(service.t('shell.logout')).toBe('Sign out of account');
    expect(localStorage.getItem('moedeiro-language')).toBe('en');
    expect(document.documentElement.lang).toBe('en');
  });

  it('interpolates translation parameters', () => {
    localStorage.setItem('moedeiro-language', 'pt-BR');
    const service = TestBed.inject(I18nService);

    expect(service.t('validation.username.max', { max: 50 })).toContain('50');
  });
});
