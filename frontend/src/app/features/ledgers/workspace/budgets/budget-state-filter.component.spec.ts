import { ComponentFixture, TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { BudgetStateFilterComponent } from './budget-state-filter.component';

describe('BudgetStateFilterComponent', () => {
  let fixture: ComponentFixture<BudgetStateFilterComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [BudgetStateFilterComponent],
      providers: [{ provide: I18nService, useValue: { t: vi.fn((key: string, params?: { count: number }) => params ? `${key}:${params.count}` : key) } }],
    });
    fixture = TestBed.createComponent(BudgetStateFilterComponent);
    fixture.componentRef.setInput('selected', ['ACTIVE', 'FUTURE', 'FINISHED']);
    fixture.detectChanges();
  });

  it('summarizes all, one, and multiple selected states', () => {
    expect(fixture.componentInstance.triggerLabel()).toBe('budgets.states.all');
    fixture.componentRef.setInput('selected', ['ACTIVE']);
    fixture.detectChanges();
    expect(fixture.componentInstance.triggerLabel()).toBe('budgets.states.active');
    fixture.componentRef.setInput('selected', ['ACTIVE', 'FUTURE']);
    fixture.detectChanges();
    expect(fixture.componentInstance.triggerLabel()).toBe('budgets.states.count:2');
  });

  it('emits states in canonical order but never permits an empty selection', () => {
    const changed = vi.fn();
    fixture.componentInstance.selectedChange.subscribe(changed);
    fixture.componentRef.setInput('selected', ['ACTIVE', 'FINISHED']);
    fixture.detectChanges();
    fixture.componentInstance.toggleState('ACTIVE');
    expect(changed).toHaveBeenCalledWith(['FINISHED']);

    changed.mockClear();
    fixture.componentRef.setInput('selected', ['ACTIVE']);
    fixture.detectChanges();
    fixture.componentInstance.toggleState('ACTIVE');
    expect(changed).not.toHaveBeenCalled();
  });

  it('opens and navigates the listbox from the keyboard', () => {
    const openEvent = { key: 'End', preventDefault: vi.fn() } as unknown as KeyboardEvent;
    fixture.componentInstance.handleKeydown(openEvent);
    expect(fixture.componentInstance.open()).toBe(true);
    expect(fixture.componentInstance.activeIndex()).toBe(2);

    fixture.componentInstance.handleKeydown({ key: 'ArrowDown', preventDefault: vi.fn() } as unknown as KeyboardEvent);
    expect(fixture.componentInstance.activeIndex()).toBe(0);
  });
});
