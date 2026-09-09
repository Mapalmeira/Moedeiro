import { AfterViewInit, Directive, ElementRef, inject } from '@angular/core';

@Directive({
  selector: 'input[appDropdownSearchAutofocus]',
  standalone: true,
})
export class DropdownSearchAutofocusDirective implements AfterViewInit {
  private readonly element = inject<ElementRef<HTMLInputElement>>(ElementRef);

  ngAfterViewInit(): void {
    this.element.nativeElement.focus();
  }
}
