import { TestBed } from '@angular/core/testing';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { EntitySearchSelectComponent } from './entity-search-select.component';

describe('EntitySearchSelectComponent geometry', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    document.body.style.overflowY = '';
    document.documentElement.style.overflowY = '';
  });

  function create() {
    TestBed.configureTestingModule({ imports: [EntitySearchSelectComponent] });
    const fixture = TestBed.createComponent(EntitySearchSelectComponent);
    fixture.componentRef.setInput('options', [{ value: 'account', label: 'Account' }]);
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    host.style.setProperty('--space-2', '8px');
    host.style.setProperty('--button-shadow-offset', '4px');
    host.style.setProperty('--search-dropdown-max-height', '340px');
    const trigger = host.querySelector<HTMLElement>('.entity-search-select__trigger')!;
    vi.spyOn(trigger, 'getBoundingClientRect').mockReturnValue({ top: 400, bottom: 444 } as DOMRect);
    vi.spyOn(window, 'innerHeight', 'get').mockReturnValue(1000);
    const boundary = host.parentElement!;
    boundary.style.overflowY = 'auto';
    vi.spyOn(boundary, 'getBoundingClientRect').mockReturnValue({ top: 350, bottom: 900 } as DOMRect);
    vi.spyOn(boundary, 'clientHeight', 'get').mockReturnValue(550);
    return { fixture, component: fixture.componentInstance, host, trigger, boundary };
  }

  it('uses the visible scroll container, not the space above it in the window', () => {
    const { component } = create();
    component.openList();
    expect(component.opensUp()).toBe(false);
    expect(component.availableHeight()).toBe(444);
  });

  it('opens upward when the visible space below is insufficient', () => {
    const { component, trigger, boundary } = create();
    vi.spyOn(trigger, 'getBoundingClientRect').mockReturnValue({ top: 700, bottom: 744 } as DOMRect);
    vi.spyOn(boundary, 'clientHeight', 'get').mockReturnValue(450);
    component.openList();
    expect(component.opensUp()).toBe(true);
    expect(component.availableHeight()).toBe(342);
  });

  it('repositions on ancestor scrolling and measures the full options list', () => {
    const { fixture, component, host, trigger, boundary } = create();
    component.openList();
    fixture.detectChanges();
    const panel = host.querySelector<HTMLElement>('.entity-search-select__panel')!;
    const list = host.querySelector<HTMLElement>('.entity-search-select__list')!;
    vi.spyOn(panel, 'offsetHeight', 'get').mockReturnValue(120);
    vi.spyOn(list, 'clientHeight', 'get').mockReturnValue(60);
    vi.spyOn(list, 'scrollHeight', 'get').mockReturnValue(600);
    vi.spyOn(trigger, 'getBoundingClientRect').mockReturnValue({ top: 760, bottom: 804 } as DOMRect);
    boundary.dispatchEvent(new Event('scroll'));
    expect(component.opensUp()).toBe(true);
    expect(component.availableHeight()).toBe(402);
  });

  it('intersects nested clipping ancestors', () => {
    const { component, host } = create();
    const boundary = host.parentElement!.parentElement!;
    boundary.style.overflowY = 'hidden';
    vi.spyOn(boundary, 'getBoundingClientRect').mockReturnValue({ top: 380, bottom: 650 } as DOMRect);
    vi.spyOn(boundary, 'clientHeight', 'get').mockReturnValue(270);
    component.openList();
    expect(component.opensUp()).toBe(false);
    expect(component.availableHeight()).toBe(194);
  });

  it('observes container resizing while open and releases the observer on selection', async () => {
    const observe = vi.fn();
    const disconnect = vi.fn();
    let resized = () => {};
    vi.stubGlobal('ResizeObserver', class {
      constructor(callback: () => void) { resized = callback; }
      observe = observe;
      disconnect = disconnect;
    });
    const { fixture, component, host, boundary, trigger } = create();
    component.openList();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(observe).toHaveBeenCalledWith(boundary);
    const list = host.querySelector<HTMLElement>('.entity-search-select__list')!;
    vi.spyOn(list, 'scrollHeight', 'get').mockReturnValue(340);
    vi.spyOn(trigger, 'getBoundingClientRect').mockReturnValue({ top: 870, bottom: 914 } as DOMRect);
    resized();
    expect(component.opensUp()).toBe(true);
    component.choose('account');
    expect(disconnect).toHaveBeenCalled();
    expect(component.open()).toBe(false);
  });

  it('focuses search without scrolling the page to the popup', () => {
    const { fixture, component } = create();
    const focus = vi.spyOn(HTMLInputElement.prototype, 'focus');
    component.openList();
    fixture.detectChanges();
    expect(focus).toHaveBeenCalledWith({ preventScroll: true });
  });
});
