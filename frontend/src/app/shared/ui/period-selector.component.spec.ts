import { TestBed } from '@angular/core/testing';
import { describe, expect, it, vi } from 'vitest';
import { I18nService } from '../../core/i18n/i18n.service';
import { PeriodSelectorComponent } from './period-selector.component';

describe('PeriodSelectorComponent', () => {
  function create(mode: 'month' | 'range') {
    TestBed.configureTestingModule({
      imports: [PeriodSelectorComponent],
      providers: [{ provide: I18nService, useValue: { t: (key: string) => key } }],
    });
    const fixture = TestBed.createComponent(PeriodSelectorComponent);
    fixture.componentRef.setInput('mode', mode);
    fixture.componentRef.setInput('month', '2026-09');
    fixture.componentRef.setInput('rangeFromDate', '2026-09-01');
    fixture.componentRef.setInput('rangeToDate', '2026-09-30');
    fixture.detectChanges();
    return fixture;
  }

  it('exposes the selected mode and emits mode changes', () => {
    const fixture = create('month');
    const modeChange = vi.fn();
    fixture.componentInstance.modeChange.subscribe(modeChange);
    const buttons = (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('.period-selector__switch button');

    expect(buttons[0]?.getAttribute('aria-pressed')).toBe('true');
    expect(buttons[1]?.getAttribute('aria-pressed')).toBe('false');
    buttons[1]?.click();

    expect(modeChange).toHaveBeenCalledWith('range');
  });

  it('emits both ends of a custom date range', () => {
    const fixture = create('range');
    const fromChange = vi.fn();
    const toChange = vi.fn();
    fixture.componentInstance.rangeFromDateChange.subscribe(fromChange);
    fixture.componentInstance.rangeToDateChange.subscribe(toChange);
    const inputs = (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLInputElement>('app-date-input input');

    inputs[0]!.value = '2026-09-01';
    inputs[0]!.dispatchEvent(new Event('input'));
    inputs[1]!.value = '2026-09-30';
    inputs[1]!.dispatchEvent(new Event('input'));

    expect(fromChange).toHaveBeenCalledWith('2026-09-01');
    expect(toChange).toHaveBeenCalledWith('2026-09-30');
  });
});
