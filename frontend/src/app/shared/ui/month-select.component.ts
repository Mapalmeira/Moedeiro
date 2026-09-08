import { ChangeDetectionStrategy, Component, ElementRef, HostListener, computed, inject, input, output, signal } from '@angular/core';
import { ENTITY_BADGE_DEFAULT_SYMBOL_SIZE } from '../ledger/entity-badge.component';
import { IconComponent } from './icon.component';

interface MonthOption {
  value: number;
  label: string;
}

@Component({
  selector: 'app-month-select',
  standalone: true,
  imports: [IconComponent],
  template: `
    <div class="month-select">
      <button type="button" class="month-select__trigger ui-select-trigger ui-trigger-with-icon" (click)="toggle()"
        [attr.aria-label]="ariaLabel()" [attr.aria-expanded]="open()">
        <span class="month-select__icon ui-icon-badge ui-icon-badge--neutral ui-projected-icon" aria-hidden="true"><app-icon name="calendar" [size]="triggerIconSize" /></span>
        <span class="ui-trigger-content"><strong class="ui-trigger-value">{{ displayValue() }}</strong></span>
        <app-icon class="ui-select-chevron" name="chevron-down" [size]="16" />
      </button>

      @if (open()) {
        <div class="month-select__panel ui-dropdown-panel">
          <div class="month-select__year">
            <button type="button" class="icon-button month-select__year-nav" (click)="changeYear(-1)" [attr.aria-label]="previousYearLabel()">
              <app-icon name="chevron-left" [size]="17" />
            </button>
            <input class="month-select__year-input" type="text" inputmode="numeric" maxlength="4" autocomplete="off"
              [attr.aria-label]="yearLabel()" [value]="displayYear()" (input)="updateYear($event)" />
            <button type="button" class="icon-button month-select__year-nav" (click)="changeYear(1)" [attr.aria-label]="nextYearLabel()">
              <app-icon name="chevron-right" [size]="17" />
            </button>
          </div>
          <div class="month-select__months" role="listbox" [attr.aria-label]="ariaLabel()">
            @for (month of months(); track month.value) {
              <button type="button" class="ui-choice month-select__month"
                [class.ui-choice--selected]="isSelected(month.value)"
                [attr.aria-selected]="isSelected(month.value)"
                (click)="chooseMonth(month.value)">{{ month.label }}</button>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: `
    :host { display: block; min-width: 0; }
    .month-select { position: relative; min-width: 0; }
    .month-select__trigger { width: 100%; height: var(--control-height); padding-block: 0; text-align: left; }
    .month-select__panel { position: absolute; z-index: var(--layer-dropdown); top: calc(100% + var(--space-2)); left: 0; width: min(340px, 84vw); }
    .month-select__year { display: grid; grid-template-columns: var(--icon-button-size) minmax(0, 1fr) var(--icon-button-size); align-items: center; gap: var(--space-2); }
    .month-select__year-nav { border-width: var(--border-width); border-color: var(--line-strong); }
    .month-select__year-input { width: 100%; height: var(--icon-button-size); min-width: 0; padding: 0 var(--space-2); border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-sm); outline: none; background: var(--surface); color: var(--text); text-align: center; font-size: var(--control-font-size); font-weight: 800; font-variant-numeric: tabular-nums; }
    .month-select__year-input:focus { border-color: var(--green-strong); box-shadow: 0 0 0 3px color-mix(in srgb, var(--green) 32%, transparent); }
    .month-select__months { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-2); }
    .month-select__month { min-width: 0; min-height: var(--menu-item-height); padding-inline: var(--space-2); }
    @media (max-width: 420px) {
      .month-select__panel { width: min(300px, calc(100vw - (2 * var(--space-4)))); }
      .month-select__months { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MonthSelectComponent {
  readonly triggerIconSize = ENTITY_BADGE_DEFAULT_SYMBOL_SIZE;
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly value = input.required<string>();
  readonly locale = input('pt-BR');
  readonly ariaLabel = input('');
  readonly previousYearLabel = input('Previous year');
  readonly nextYearLabel = input('Next year');
  readonly yearLabel = input('Year');
  readonly valueChange = output<string>();

  readonly open = signal(false);
  readonly displayYear = signal(new Date().getFullYear());
  readonly months = computed<MonthOption[]>(() => {
    const formatter = new Intl.DateTimeFormat(this.locale(), { month: 'short', timeZone: 'UTC' });
    return Array.from({ length: 12 }, (_, index) => ({
      value: index + 1,
      label: this.capitalize(formatter.format(new Date(Date.UTC(2026, index, 1))).replace('.', '')),
    }));
  });
  readonly displayValue = computed(() => {
    const parsed = this.parse(this.value());
    if (!parsed) return this.value();
    const month = new Intl.DateTimeFormat(this.locale(), { month: 'long', timeZone: 'UTC' })
      .format(new Date(Date.UTC(parsed.year, parsed.month - 1, 1)));
    return `${this.capitalize(month)} ${parsed.year}`;
  });

  @HostListener('document:mousedown', ['$event'])
  closeOutside(event: MouseEvent): void {
    if (this.open() && !this.host.nativeElement.contains(event.target as Node)) this.close();
  }

  @HostListener('document:keydown.escape')
  closeOnEscape(): void {
    this.close();
  }

  toggle(): void {
    if (this.open()) {
      this.close();
      return;
    }
    this.displayYear.set(this.parse(this.value())?.year ?? new Date().getFullYear());
    this.open.set(true);
  }

  close(): void {
    this.open.set(false);
  }

  changeYear(delta: number): void {
    this.displayYear.update(year => Math.max(1, Math.min(9999, year + delta)));
  }

  updateYear(event: Event): void {
    const year = Number((event.target as HTMLInputElement).value);
    if (Number.isInteger(year) && year >= 1 && year <= 9999) this.displayYear.set(year);
  }

  isSelected(month: number): boolean {
    const parsed = this.parse(this.value());
    return parsed?.year === this.displayYear() && parsed.month === month;
  }

  chooseMonth(month: number): void {
    this.valueChange.emit(`${String(this.displayYear()).padStart(4, '0')}-${String(month).padStart(2, '0')}`);
    this.close();
  }

  private capitalize(value: string): string {
    return value ? value[0].toLocaleUpperCase(this.locale()) + value.slice(1) : value;
  }

  private parse(value: string): { year: number; month: number } | null {
    const match = /^(\d{4})-(\d{2})$/.exec(value);
    if (!match) return null;
    const year = Number(match[1]);
    const month = Number(match[2]);
    return month >= 1 && month <= 12 ? { year, month } : null;
  }
}
