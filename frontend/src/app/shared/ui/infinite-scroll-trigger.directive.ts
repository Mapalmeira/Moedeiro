import { AfterViewInit, Directive, ElementRef, OnDestroy, input, output } from '@angular/core';

@Directive({
  selector: '[appInfiniteScrollTrigger]',
  standalone: true,
})
export class InfiniteScrollTriggerDirective implements AfterViewInit, OnDestroy {
  private readonly element: ElementRef<HTMLElement>;
  private observer: IntersectionObserver | null = null;

  readonly enabled = input(true);
  readonly rootMargin = input('160px 0px');
  readonly triggered = output<void>();

  constructor(element: ElementRef<HTMLElement>) {
    this.element = element;
  }

  ngAfterViewInit(): void {
    if (typeof IntersectionObserver === 'undefined') return;

    this.observer = new IntersectionObserver((entries) => {
      if (!this.enabled() || !entries.some(entry => entry.isIntersecting)) return;
      this.triggered.emit();
    }, {
      root: null,
      rootMargin: this.rootMargin(),
      threshold: 0,
    });
    this.observer.observe(this.element.nativeElement);
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
    this.observer = null;
  }
}
