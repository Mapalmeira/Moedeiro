import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, HostListener, OnDestroy, input, output, viewChild } from '@angular/core';

@Component({
  selector: 'app-dialog-shell',
  standalone: true,
  host: { style: 'display: contents' },
  template: `
    <div class="ui-dialog-backdrop" (click)="dismiss.emit()" aria-hidden="true"></div>
    <div class="ui-dialog-layer" [style.--dialog-width]="dialogWidth() || null">
      <div class="ui-dialog-frame ui-projected-surface ui-projection--dialog">
        <section #surface class="ui-dialog-surface" [attr.role]="role()" aria-modal="true"
          [attr.aria-label]="ariaLabel() || null" [attr.aria-labelledby]="ariaLabelledby() || null" tabindex="-1">
          <ng-content />
        </section>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DialogShellComponent implements AfterViewInit, OnDestroy {
  private static readonly stack: DialogShellComponent[] = [];

  readonly role = input<'dialog' | 'alertdialog'>('dialog');
  readonly ariaLabel = input('');
  readonly ariaLabelledby = input('');
  readonly dialogWidth = input('');
  readonly dismiss = output<void>();
  readonly surface = viewChild.required<ElementRef<HTMLElement>>('surface');
  private readonly previousFocus = typeof document === 'undefined' ? null : document.activeElement as HTMLElement | null;

  ngAfterViewInit(): void {
    DialogShellComponent.stack.push(this);
    queueMicrotask(() => {
      if (this.isTopmost()) this.focusInitialElement();
    });
  }

  ngOnDestroy(): void {
    const wasTopmost = this.isTopmost();
    const index = DialogShellComponent.stack.lastIndexOf(this);
    if (index >= 0) DialogShellComponent.stack.splice(index, 1);
    if (wasTopmost && this.previousFocus?.isConnected) this.previousFocus.focus({ preventScroll: true });
  }

  @HostListener('document:keydown.escape', ['$event'])
  closeOnEscape(event: Event): void {
    if (!this.isTopmost() || event.defaultPrevented) return;
    event.preventDefault();
    this.dismiss.emit();
  }

  @HostListener('document:keydown.tab', ['$event'])
  trapFocus(event: Event): void {
    if (!this.isTopmost()) return;
    const keyboardEvent = event as KeyboardEvent;
    const focusable = this.focusableElements();
    if (!focusable.length) {
      event.preventDefault();
      this.surface().nativeElement.focus({ preventScroll: true });
      return;
    }
    const active = document.activeElement;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (keyboardEvent.shiftKey && (active === first || !this.surface().nativeElement.contains(active))) {
      event.preventDefault();
      last.focus();
    } else if (!keyboardEvent.shiftKey && (active === last || !this.surface().nativeElement.contains(active))) {
      event.preventDefault();
      first.focus();
    }
  }

  private isTopmost(): boolean {
    return DialogShellComponent.stack[DialogShellComponent.stack.length - 1] === this;
  }

  private focusInitialElement(): void {
    const [first] = this.focusableElements();
    (first ?? this.surface().nativeElement).focus({ preventScroll: true });
  }

  private focusableElements(): HTMLElement[] {
    const selector = 'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])';
    return Array.from(this.surface().nativeElement.querySelectorAll<HTMLElement>(selector))
      .filter(element => !element.hasAttribute('hidden') && element.getAttribute('aria-hidden') !== 'true');
  }
}
