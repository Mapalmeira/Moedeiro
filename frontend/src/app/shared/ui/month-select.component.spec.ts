import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { MonthSelectComponent } from './month-select.component';

describe('MonthSelectComponent', () => {
  it('capitalizes standalone month labels and exposes listbox options', () => {
    const fixture = TestBed.createComponent(MonthSelectComponent);
    fixture.componentRef.setInput('value', '2026-09');
    fixture.detectChanges();

    const component = fixture.componentInstance;
    const capitalize = (value: string) => value[0]!.toLocaleUpperCase() + value.slice(1);
    const expectedShort = capitalize(new Intl.DateTimeFormat(undefined, { month: 'short' }).format(new Date(2026, 8, 1)));
    const expectedLong = capitalize(new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(new Date(2026, 8, 1)));
    expect(component.months()[8]?.label).toBe(expectedShort);
    expect(component.displayValue()).toBe(expectedLong);

    component.toggle();
    fixture.detectChanges();
    const options = (fixture.nativeElement as HTMLElement).querySelectorAll('[role="option"]');
    expect(options).toHaveLength(12);
  });
});
