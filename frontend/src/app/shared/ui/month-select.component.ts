import { ChangeDetectionStrategy, Component, computed, inject, input, output, signal } from '@angular/core';
import { DismissiblePopoverDirective } from './dismissible-popover.directive';
import { IconComponent } from './icon.component';
import { isListboxNavigationKey, nextListboxIndex } from './listbox-navigation';

interface MonthOption {
  value: number;
  label: string;
}

@Component({
  selector: 'app-month-select',
  standalone: true,
  imports: [DismissiblePopoverDirective, IconComponent],
  template: `
    <div class="month-select" [appDismissiblePopover]="open()" (dismiss)="close()">
      <button type="button" class="month-select__trigger ui-select-trigger ui-trigger-with-icon" (click)="toggle()"
        [attr.aria-label]="ariaLabel()" aria-haspopup="listbox" [attr.aria-expanded]="open()" [attr.aria-controls]="listId"
        [attr.aria-activedescendant]="open() ? activeOptionId() : null" (keydown)="handleTriggerKeydown($event)">
        <span class="month-select__icon ui-icon-badge ui-icon-badge--neutral ui-projected-icon" aria-hidden="true"><app-icon name="LucideCalendarDays" size="badge" /></span>
        <span class="ui-trigger-content"><strong class="ui-trigger-value ui-truncate">{{ displayValue() }}</strong></span>
        <app-icon class="ui-select-chevron" name="LucideChevronDown" size="compact" />
      </button>

      @if (open()) {
        <div class="month-select__panel ui-dropdown-panel">
          <div class="month-select__year">
            <button type="button" class="icon-button month-select__year-nav" (click)="changeYear(-1)" [attr.aria-label]="previousYearLabel()">
              <app-icon name="LucideChevronLeft" size="compact" />
            </button>
            <input class="month-select__year-input" type="text" inputmode="numeric" maxlength="4" autocomplete="off"
              [attr.aria-label]="yearLabel()" [value]="displayYear()" (input)="updateYear($event)" />
            <button type="button" class="icon-button month-select__year-nav" (click)="changeYear(1)" [attr.aria-label]="nextYearLabel()">
              <app-icon name="LucideChevronRight" size="compact" />
            </button>
          </div>
          <div class="month-select__months" role="listbox" [id]="listId" [attr.aria-label]="ariaLabel()">
            @for (month of months(); track month.value) {
              <button type="button" class="ui-choice month-select__month" role="option" [id]="optionId(month.value)" tabindex="-1"
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
    .month-select__panel { position: absolute; z-index: var(--layer-dropdown); top: calc(100% + var(--space-2)); left: 0; width: 100%; }
    .month-select__year { display: grid; grid-template-columns: var(--icon-button-size) minmax(0, 1fr) var(--icon-button-size); align-items: center; gap: var(--space-2); }
    .month-select__year-nav { border-width: var(--border-width); border-color: var(--line-strong); }
    .month-select__year-input { width: 100%; height: var(--icon-button-size); min-width: 0; padding: 0 var(--space-2); border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-sm); outline: none; background: var(--surface); color: var(--text); text-align: center; font-size: var(--control-font-size); font-weight: 800; font-variant-numeric: tabular-nums; }
    .month-select__year-input:focus { border-color: var(--green-strong); box-shadow: 0 0 0 3px color-mix(in srgb, var(--green) 32%, transparent); }
    .month-select__months { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-2); }
    .month-select__month { min-width: 0; min-height: var(--menu-item-height); padding-inline: var(--space-2); }
    @media (max-width: 420px) {
      .month-select__months { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MonthSelectComponent {
  private static nextId = 0;
  readonly value = input.required<string>();
  readonly ariaLabel = input('');
  readonly previousYearLabel = input('Previous year');
  readonly nextYearLabel = input('Next year');
  readonly yearLabel = input('Year');
  readonly valueChange = output<string>();

  readonly open = signal(false);
  readonly activeMonth = signal(1);
  readonly listId = `month-select-${MonthSelectComponent.nextId++}`;
  readonly activeOptionId = () => this.optionId(this.activeMonth());
  readonly displayYear = signal(new Date().getFullYear());
  readonly months = computed<MonthOption[]>(() => {
    const formatter = new Intl.DateTimeFormat(undefined, { month: 'short' });
    return Array.from({ length: 12 }, (_, index) => ({
      value: index + 1,
      label: this.capitalizeLabel(formatter.format(new Date(2026, index, 1))),
    }));
  });
  readonly displayValue = computed(() => {
    const parsed = this.parse(this.value());
    if (!parsed) return this.value();
    const label = new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' })
      .format(new Date(parsed.year, parsed.month - 1, 1));
    return this.capitalizeLabel(label);
  });

  toggle(): void {
    if (this.open()) {
      this.close();
      return;
    }
    const parsed = this.parse(this.value());
    this.displayYear.set(parsed?.year ?? new Date().getFullYear());
    this.activeMonth.set(parsed?.month ?? new Date().getMonth() + 1);
    this.open.set(true);
  }

  close(): void {
    this.open.set(false);
  }

  handleTriggerKeydown(event: KeyboardEvent): void {
    if (isListboxNavigationKey(event.key)) {
      event.preventDefault();
      if (!this.open()) this.toggle();
      else this.activeMonth.set(nextListboxIndex(this.activeMonth() - 1, 12, event.key) + 1);
      return;
    }
    if (this.open() && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      this.chooseMonth(this.activeMonth());
    }
  }

  optionId(month: number): string { return `${this.listId}-option-${month}`; }

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
    this.activeMonth.set(month);
    this.valueChange.emit(`${String(this.displayYear()).padStart(4, '0')}-${String(month).padStart(2, '0')}`);
    this.close();
  }

  private capitalizeLabel(value: string): string {
    if (!value) return value;
    return value[0]!.toLocaleUpperCase() + value.slice(1);
  }

  private parse(value: string): { year: number; month: number } | null {
    const match = /^(\d{4})-(\d{2})$/.exec(value);
    if (!match) return null;
    const year = Number(match[1]);
    const month = Number(match[2]);
    return month >= 1 && month <= 12 ? { year, month } : null;
  }
}
