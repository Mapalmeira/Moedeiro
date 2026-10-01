import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { InfiniteScrollTriggerDirective } from './infinite-scroll-trigger.directive';

@Component({
  imports: [InfiniteScrollTriggerDirective],
  template: `<div appInfiniteScrollTrigger [enabled]="enabled" [rootMargin]="margin" (triggered)="count = count + 1"></div>`,
})
class HostComponent {
  enabled = true;
  margin = '80px 0px';
  count = 0;
}

describe('InfiniteScrollTriggerDirective', () => {
  let callback: IntersectionObserverCallback;
  let observe: ReturnType<typeof vi.fn>;
  let disconnect: ReturnType<typeof vi.fn>;
  let fixture: ComponentFixture<HostComponent>;

  beforeEach(() => {
    observe = vi.fn();
    disconnect = vi.fn();
    class Observer {
      constructor(next: IntersectionObserverCallback, readonly options?: IntersectionObserverInit) { callback = next; }
      observe = observe;
      disconnect = disconnect;
    }
    vi.stubGlobal('IntersectionObserver', Observer);
    TestBed.configureTestingModule({ imports: [HostComponent] });
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  it('emits when the sentinel intersects and loading is enabled', () => {
    callback([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(fixture.componentInstance.count).toBe(1);
    expect(observe).toHaveBeenCalledOnce();
  });

  it('ignores intersections while disabled and disconnects on destroy', () => {
    fixture.destroy();
    disconnect.mockClear();
    fixture = TestBed.createComponent(HostComponent);
    fixture.componentInstance.enabled = false;
    fixture.detectChanges();
    callback([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(fixture.componentInstance.count).toBe(0);

    fixture.destroy();
    expect(disconnect).toHaveBeenCalledOnce();
  });
});
