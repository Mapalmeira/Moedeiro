import { DestroyRef, Directive, ElementRef, Injector, afterNextRender, inject, input, output } from '@angular/core';

/** Reports how many whole list rows fit in the current vertical space. */
@Directive({ selector: '[appDiscreteListCapacity]', standalone: true })
export class DiscreteListCapacityDirective {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly destroyRef = inject(DestroyRef);
  private readonly injector = inject(Injector);
  readonly maxCapacity = input(10);
  readonly capacityChange = output<number>();
  private resizeObserver?: ResizeObserver;
  private mutationObserver?: MutationObserver;
  private lastCapacity = 0;

  constructor() {
    afterNextRender(() => this.start(), { injector: this.injector });
    this.destroyRef.onDestroy(() => {
      this.resizeObserver?.disconnect();
      this.mutationObserver?.disconnect();
    });
  }

  measure(): void {
    const list = this.host.nativeElement;
    const row = list.querySelector<HTMLElement>(':scope > a');
    const rowHeight = row ? Number.parseFloat(getComputedStyle(row).minHeight) : Number.NaN;
    const listHeight = list.getBoundingClientRect().height;
    const capacity = Number.isFinite(rowHeight) && rowHeight > 0 && listHeight > 0
      ? Math.min(this.maxCapacity(), Math.max(1, Math.floor(listHeight / rowHeight)))
      : 1;
    if (capacity === this.lastCapacity) return;
    this.lastCapacity = capacity;
    list.style.setProperty('--home-preview-capacity', String(capacity));
    this.capacityChange.emit(capacity);
  }

  private start(): void {
    const list = this.host.nativeElement;
    if (typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => this.measure());
      this.resizeObserver.observe(list);
    }
    if (typeof MutationObserver !== 'undefined') {
      this.mutationObserver = new MutationObserver(() => this.measure());
      this.mutationObserver.observe(list, { childList: true });
    }
    this.measure();
  }
}
