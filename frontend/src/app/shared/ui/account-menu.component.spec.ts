import { ComponentFixture, TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nService } from '../../core/i18n/i18n.service';
import { AccountMenuComponent } from './account-menu.component';

describe('AccountMenuComponent', () => {
  let fixture: ComponentFixture<AccountMenuComponent>;
  let component: AccountMenuComponent;

  beforeEach(async () => {
    localStorage.setItem('moedeiro-language', 'pt-BR');
    await TestBed.configureTestingModule({
      imports: [AccountMenuComponent],
      providers: [I18nService],
    }).compileComponents();

    fixture = TestBed.createComponent(AccountMenuComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('userName', 'alice');
    fixture.componentRef.setInput('fullWidth', true);
    fixture.detectChanges();
  });

  it('shows the username and exposes dropdown state through aria-expanded', () => {
    const trigger = fixture.nativeElement.querySelector('.account-trigger') as HTMLButtonElement;

    expect(trigger.textContent).toContain('alice');
    expect(trigger.getAttribute('aria-expanded')).toBe('false');

    trigger.click();
    fixture.detectChanges();

    expect(component.open()).toBe(true);
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
    expect(fixture.nativeElement.querySelector('.account-dropdown')).not.toBeNull();
  });

  it('renders an optional inline context with the account name in its accessible name', () => {
    fixture.componentRef.setInput('label', 'Minha conta');
    fixture.detectChanges();

    const trigger = fixture.nativeElement.querySelector('.account-trigger') as HTMLButtonElement;

    expect(fixture.nativeElement.querySelector('.ui-trigger-context')?.textContent).toContain('Minha conta');
    expect(trigger.getAttribute('aria-label')).toBe('Minha conta: alice');
  });

  it('closes and emits the selected account action', () => {
    const preferences = vi.fn();
    component.preferences.subscribe(preferences);
    component.open.set(true);
    fixture.detectChanges();

    component.choosePreferences();

    expect(preferences).toHaveBeenCalledOnce();
    expect(component.open()).toBe(false);
  });

  it('closes on Escape', () => {
    component.open.set(true);
    component.closeOnEscape();
    expect(component.open()).toBe(false);
  });
});
