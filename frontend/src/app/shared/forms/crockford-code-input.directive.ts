import { Directive, ElementRef, forwardRef, HostListener, inject, Renderer2 } from '@angular/core';
import { AbstractControl, ControlValueAccessor, NG_VALIDATORS, NG_VALUE_ACCESSOR, ValidationErrors, Validator } from '@angular/forms';

export const CROCKFORD_CODE_PATTERN = /^[0-9ABCDEFGHJKMNPQRSTVWXYZ]{16}$/;

export function normalizeCrockfordCode(value: string): string {
  return value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 16);
}

export function formatCrockfordCode(value: string): string {
  const raw = normalizeCrockfordCode(value);
  return raw.match(/.{1,4}/g)?.join('-') ?? '';
}

@Directive({
  selector: 'input[appCrockfordCode]',
  standalone: true,
  providers: [
    { provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => CrockfordCodeInputDirective), multi: true },
    { provide: NG_VALIDATORS, useExisting: forwardRef(() => CrockfordCodeInputDirective), multi: true },
  ],
  host: {
    '[attr.maxlength]': '"19"',
    '[attr.autocapitalize]': '"characters"',
    '[attr.spellcheck]': '"false"',
  },
})
export class CrockfordCodeInputDirective implements ControlValueAccessor, Validator {
  private readonly element = inject<ElementRef<HTMLInputElement>>(ElementRef);
  private readonly renderer = inject(Renderer2);
  private onChange: (value: string) => void = () => undefined;
  private onTouched: () => void = () => undefined;

  @HostListener('beforeinput', ['$event'])
  blockNonAlphanumeric(event: InputEvent): void {
    if (event.inputType === 'insertFromPaste') return;
    if (event.data && /[^A-Za-z0-9]/.test(event.data)) event.preventDefault();
  }

  @HostListener('input', ['$event'])
  onInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    const cursor = input.selectionStart ?? input.value.length;
    const rawBeforeCursor = normalizeCrockfordCode(input.value.slice(0, cursor)).length;
    const formatted = formatCrockfordCode(input.value);
    this.renderer.setProperty(input, 'value', formatted);
    this.onChange(formatted);

    const nextCursor = Math.min(formatted.length, rawBeforeCursor + Math.floor(Math.max(rawBeforeCursor - 1, 0) / 4));
    queueMicrotask(() => input.setSelectionRange(nextCursor, nextCursor));
  }

  @HostListener('blur')
  onBlur(): void {
    this.onTouched();
  }

  writeValue(value: string | null): void {
    this.renderer.setProperty(this.element.nativeElement, 'value', formatCrockfordCode(value ?? ''));
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(disabled: boolean): void {
    this.renderer.setProperty(this.element.nativeElement, 'disabled', disabled);
  }

  validate(control: AbstractControl): ValidationErrors | null {
    const value = String(control.value ?? '');
    if (!value) return null;
    return CROCKFORD_CODE_PATTERN.test(normalizeCrockfordCode(value)) ? null : { crockfordCode: true };
  }
}
