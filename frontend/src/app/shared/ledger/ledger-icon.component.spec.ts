import { ComponentFixture, TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';
import { LUCIDE_ICON_CATALOG } from './lucide-icon-catalog';
import { LedgerIconComponent } from './ledger-icon.component';

describe('LedgerIconComponent', () => {
  let fixture: ComponentFixture<LedgerIconComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [LedgerIconComponent] }).compileComponents();
    fixture = TestBed.createComponent(LedgerIconComponent);
  });

  it('renders Unicode content as one centered, non-wrapping unit regardless of character count', () => {
    fixture.componentRef.setInput('icon', 'unicode:💰💰💰');
    fixture.componentRef.setInput('size', 54);
    fixture.detectChanges();

    const unicode = fixture.nativeElement.querySelector('.unicode-icon') as HTMLElement;
    const style = getComputedStyle(unicode);

    expect(unicode.textContent?.trim()).toBe('💰💰💰');
    expect(style.position).toBe('absolute');
    expect(style.left).toBe('50%');
    expect(style.top).toBe('50%');
    expect(style.whiteSpace).toBe('nowrap');
    expect(unicode.className).toBe('unicode-icon');
  });

  it('uses the same Unicode styling for one and three characters', () => {
    fixture.componentRef.setInput('icon', 'unicode:R$');
    fixture.detectChanges();
    const first = getComputedStyle(fixture.nativeElement.querySelector('.unicode-icon') as HTMLElement).fontSize;

    fixture.componentRef.setInput('icon', 'unicode:💰💰💰');
    fixture.detectChanges();
    const second = getComputedStyle(fixture.nativeElement.querySelector('.unicode-icon') as HTMLElement).fontSize;

    expect(second).toBe(first);
  });

  it('renders prefixed Lucide values through the catalog', () => {
    const entry = LUCIDE_ICON_CATALOG[0];
    expect(entry).toBeDefined();

    fixture.componentRef.setInput('icon', `lucide:${entry!.id}`);
    fixture.detectChanges();

    expect(fixture.componentInstance.lucideComponent()).not.toBeNull();
    expect(fixture.nativeElement.querySelector('svg')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('.unicode-icon')).toBeNull();
  });

  it('does not interpret bare legacy values as Lucide icons', () => {
    fixture.componentRef.setInput('icon', 'WalletCards');
    fixture.detectChanges();

    expect(fixture.componentInstance.lucideComponent()).toBeNull();
    expect(fixture.nativeElement.querySelector('.unicode-icon')?.textContent).toBe('');
  });
});
