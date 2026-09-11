import { Directive, ElementRef, HostListener, inject, input, output } from '@angular/core';

/** Shared dismissal behavior for anchored dropdowns/popovers. */
@Directive({
  selector: '[appDismissiblePopover]',
  standalone: true,
})
export class DismissiblePopoverDirective {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  readonly active = input(false, { alias: 'appDismissiblePopover' });
  readonly dismiss = output<void>();

  @HostListener('document:mousedown', ['$event'])
  closeWhenClickingOutside(event: MouseEvent): void {
    if (this.active() && !this.host.nativeElement.contains(event.target as Node)) this.dismiss.emit();
  }

  @HostListener('document:keydown.escape', ['$event'])
  closeOnEscape(event: Event): void {
    if (!this.active()) return;
    event.preventDefault();
    this.dismiss.emit();
  }
}
