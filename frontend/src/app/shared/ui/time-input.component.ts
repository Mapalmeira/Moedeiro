import { ChangeDetectionStrategy, Component, effect, forwardRef, input, output, signal } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { TimeFormat } from '../../core/preferences/preferences.models';
import { formatTimeInput, parseTimeInput } from '../../core/preferences/date-time-format';

@Component({
  selector: 'app-time-input',
  standalone: true,
  providers: [{ provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => TimeInputComponent), multi: true }],
  template: `<input class="ui-field-control" type="text" autocomplete="off" [value]="displayValue()" [placeholder]="placeholder()"
    [required]="required()" [disabled]="disabled()" [attr.aria-label]="ariaLabel() || null" (input)="update($event)" (blur)="blur()" />`,
  styles: ':host { display: block; min-width: 0; } input { min-width: 0; }',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TimeInputComponent implements ControlValueAccessor {
  readonly value = input('');
  readonly format = input<TimeFormat>('H24');
  readonly ariaLabel = input('');
  readonly required = input(false);
  readonly valueChange = output<string>();

  readonly displayValue = signal('');
  readonly disabled = signal(false);
  readonly placeholder = signal('HH:MM');
  private controlValue = '';
  private formControlBound = false;
  private onChange: (value: string) => void = () => undefined;
  private onTouched: () => void = () => undefined;

  constructor() {
    effect(() => {
      const format = this.format();
      this.placeholder.set(format === 'H12' ? 'HH:MM AM' : 'HH:MM');
      const value = this.formControlBound ? this.controlValue : this.value();
      this.displayValue.set(formatTimeInput(value, format));
    });
  }

  writeValue(value: string | null): void {
    this.formControlBound = true;
    this.controlValue = value ?? '';
    this.displayValue.set(formatTimeInput(this.controlValue, this.format()));
  }

  registerOnChange(onChange: (value: string) => void): void { this.onChange = onChange; }
  registerOnTouched(onTouched: () => void): void { this.onTouched = onTouched; }
  setDisabledState(disabled: boolean): void { this.disabled.set(disabled); }

  update(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.displayValue.set(value);
    const parsed = parseTimeInput(value, this.format());
    if (parsed) {
      this.controlValue = parsed;
      this.onChange(parsed);
      this.valueChange.emit(parsed);
    } else if (this.formControlBound) {
      this.controlValue = '';
      this.onChange('');
    }
  }

  blur(): void {
    const value = parseTimeInput(this.displayValue(), this.format());
    if (value) this.displayValue.set(formatTimeInput(value, this.format()));
    else if (!this.formControlBound) this.valueChange.emit('');
    this.onTouched();
  }
}
