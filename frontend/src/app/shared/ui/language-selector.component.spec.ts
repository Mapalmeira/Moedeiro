import { ComponentFixture, TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';
import { I18nService } from '../../core/i18n/i18n.service';
import { LanguageSelectorComponent } from './language-selector.component';

describe('LanguageSelectorComponent', () => {
  let fixture: ComponentFixture<LanguageSelectorComponent>;
  let component: LanguageSelectorComponent;

  beforeEach(async () => {
    localStorage.setItem('moedeiro-language', 'pt-BR');
    await TestBed.configureTestingModule({
      imports: [LanguageSelectorComponent],
      providers: [I18nService],
    }).compileComponents();

    fixture = TestBed.createComponent(LanguageSelectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('uses the compact language trigger as an action and exposes its dropdown state', () => {
    const trigger = fixture.nativeElement.querySelector('.language-selector__trigger') as HTMLButtonElement;
    const name = fixture.nativeElement.querySelector('.language-selector__name') as HTMLElement;
    const languageIcon = fixture.nativeElement.querySelector('.language-selector__language-icon') as HTMLElement;

    expect(trigger.classList.contains('ui-action-press')).toBe(true);
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
    expect(name.textContent?.trim()).toBe('Português');
    expect(languageIcon).not.toBeNull();

    trigger.click();
    fixture.detectChanges();

    expect(component.open()).toBe(true);
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
    expect(fixture.nativeElement.querySelector('.language-selector__menu')).not.toBeNull();
  });

  it('positions the field appearance menu over the viewport', () => {
    fixture.componentRef.setInput('appearance', 'field');
    fixture.detectChanges();

    const trigger = fixture.nativeElement.querySelector('.language-selector__trigger') as HTMLButtonElement;
    expect(trigger.classList.contains('ui-action-press')).toBe(false);

    trigger.click();
    fixture.detectChanges();

    const menu = fixture.nativeElement.querySelector('.language-selector__menu') as HTMLElement;
    expect(menu.classList.contains('language-selector__menu--viewport-overlay')).toBe(true);
  });
});
