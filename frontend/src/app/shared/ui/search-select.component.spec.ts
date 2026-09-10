import { ComponentFixture, TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SearchSelectComponent } from './search-select.component';

describe('SearchSelectComponent', () => {
  let fixture: ComponentFixture<SearchSelectComponent>;
  let component: SearchSelectComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [SearchSelectComponent] }).compileComponents();
    fixture = TestBed.createComponent(SearchSelectComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('options', ['América/São_Paulo', 'Europe/London', 'Asia/Tokyo']);
    fixture.componentRef.setInput('value', 'America/Sao_Paulo');
    fixture.componentRef.setInput('searchPlaceholder', 'Search');
    fixture.detectChanges();
  });

  it('opens with an empty query and ignores case and accents when filtering', () => {
    component.query.set('stale');
    component.openList();
    expect(component.query()).toBe('');

    component.query.set('america/sao');
    expect(component.filteredOptions()).toEqual(['América/São_Paulo']);
  });

  it('focuses the search field when the dropdown opens', () => {
    component.openList();
    fixture.detectChanges();

    const searchInput = fixture.nativeElement.querySelector('input[type="search"]') as HTMLInputElement;
    expect(document.activeElement).toBe(searchInput);
  });

  it('emits a selected value and closes the dropdown', () => {
    const selected = vi.fn();
    component.valueChange.subscribe(selected);
    component.openList();

    component.choose('Asia/Tokyo');

    expect(selected).toHaveBeenCalledWith('Asia/Tokyo');
    expect(component.open()).toBe(false);
    expect(component.query()).toBe('');
  });

  it('selects the first filtered result on Enter', () => {
    const selected = vi.fn();
    const event = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true });
    component.valueChange.subscribe(selected);
    component.openList();
    component.query.set('asia');

    component.selectFirst(event);

    expect(selected).toHaveBeenCalledWith('Asia/Tokyo');
    expect(event.defaultPrevented).toBe(true);
  });

  it('closes when Escape is handled', () => {
    component.openList();
    component.query.set('asia');

    component.closeOnEscape();

    expect(component.open()).toBe(false);
    expect(component.query()).toBe('');
  });
});
