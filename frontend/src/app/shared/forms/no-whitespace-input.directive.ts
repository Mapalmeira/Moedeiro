import { Directive, ElementRef, HostListener, inject } from '@angular/core';

@Directive({
  selector: 'input[appNoWhitespace]',
  standalone: true,
})
export class NoWhitespaceInputDirective {
  private readonly element = inject<ElementRef<HTMLInputElement>>(ElementRef);

  @HostListener('beforeinput', ['$event'])
  blockWhitespace(event: InputEvent): void {
    if (event.data && /\s/u.test(event.data)) event.preventDefault();
  }

  @HostListener('paste', ['$event'])
  blockWhitespacePaste(event: ClipboardEvent): void {
    const value = event.clipboardData?.getData('text') ?? '';
    if (/\s/u.test(value)) event.preventDefault();
  }

  @HostListener('drop', ['$event'])
  blockWhitespaceDrop(event: DragEvent): void {
    const value = event.dataTransfer?.getData('text') ?? '';
    if (/\s/u.test(value)) event.preventDefault();
  }

  @HostListener('input')
  removeWhitespaceFromProgrammaticInput(): void {
    const input = this.element.nativeElement;
    if (!/\s/u.test(input.value)) return;

    const start = input.selectionStart ?? input.value.length;
    const beforeCursor = input.value.slice(0, start).replace(/\s+/gu, '');
    const sanitized = input.value.replace(/\s+/gu, '');

    queueMicrotask(() => {
      if (input.value === sanitized) return;
      input.value = sanitized;
      input.setSelectionRange(beforeCursor.length, beforeCursor.length);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
  }
}
