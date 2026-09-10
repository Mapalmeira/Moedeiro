import { ChangeDetectionStrategy, Component, computed, effect, forwardRef, input, output, signal } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { DateFormat } from '../../core/preferences/preferences.models';

@Component({
  selector: 'app-date-input',
  standalone: true,
  providers: [{ provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => DateInputComponent), multi: true }],
  template: `<input type="date" autocomplete="off" [value]="inputValue()" [required]="required()" [disabled]="disabled()"
    [attr.lang]="nativeLanguage()" [attr.aria-label]="ariaLabel() || null" (input)="update($event)" (blur)="onTouched()" />`,
  styles: ':host { display: block; min-width: 0; } input { width: 100%; min-width: 0; max-width: 100%; }',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DateInputComponent implements ControlValueAccessor {
  readonly value = input('');
  readonly format = input<DateFormat>('DMY');
  readonly locale = input('pt-BR');
  readonly ariaLabel = input('');
  readonly required = input(false);
  readonly valueChange = output<string>();

  readonly inputValue = signal('');
  readonly disabled = signal(false);
  readonly nativeLanguage = computed(() => {
    if (this.format() === 'MDY') return 'en-US';
    if (this.format() === 'YMD') return 'en-CA';
    return this.locale().toLowerCase().startsWith('pt') ? 'pt-BR' : 'en-GB';
  });

  private formControlBound = false;
  private onChange: (value: string) => void = () => undefined;
  onTouched: () => void = () => undefined;

  constructor() {
    effect(() => {
      const value = this.value();
      if (!this.formControlBound) this.inputValue.set(value);
    });
  }

  writeValue(value: string | null): void {
    this.formControlBound = true;
    this.inputValue.set(value ?? '');
  }

  registerOnChange(onChange: (value: string) => void): void { this.onChange = onChange; }
  registerOnTouched(onTouched: () => void): void { this.onTouched = onTouched; }
  setDisabledState(disabled: boolean): void { this.disabled.set(disabled); }

  update(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.inputValue.set(value);
    this.onChange(value);
    this.valueChange.emit(value);
  }
}
