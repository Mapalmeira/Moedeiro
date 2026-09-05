import { ComponentFixture, TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';
import { BrandLogoComponent } from './brand-logo.component';

describe('BrandLogoComponent', () => {
  let fixture: ComponentFixture<BrandLogoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [BrandLogoComponent] }).compileComponents();
    fixture = TestBed.createComponent(BrandLogoComponent);
  });

  it('builds the brand from MoedeiroIcon.svg and an HTML wordmark', () => {
    fixture.detectChanges();

    const image = fixture.nativeElement.querySelector('.brand__icon') as HTMLImageElement;
    const wordmark = fixture.nativeElement.querySelector('.brand__wordmark') as HTMLElement;

    expect(image.getAttribute('src')).toBe('/MoedeiroIcon.svg');
    expect(image.getAttribute('src')).not.toContain('logo.svg');
    expect(wordmark.textContent?.trim()).toBe('Moedeiro');
  });

  it('uses the same markup with the compact sidebar variant', () => {
    fixture.componentRef.setInput('variant', 'sidebar');
    fixture.detectChanges();

    const brand = fixture.nativeElement.querySelector('.brand') as HTMLElement;
    expect(brand.classList.contains('brand--sidebar')).toBe(true);
    expect(fixture.nativeElement.querySelectorAll('.brand__icon')).toHaveLength(1);
    expect(fixture.nativeElement.querySelectorAll('.brand__wordmark')).toHaveLength(1);
  });
});
