import { ChangeDetectionStrategy, Component, inject, input, output } from '@angular/core';
import { I18nService } from '../../core/i18n/i18n.service';
import { MonthSelectComponent } from './month-select.component';

export type PeriodMode = 'month' | 'range';

@Component({
  selector: 'app-period-selector',
  standalone: true,
  imports: [MonthSelectComponent],
  template: `
    <div class="period-selector">
      <span class="period-selector__label">{{ i18n.t('common.period') }}</span>
      <div class="period-selector__row">
        <div class="period-selector__switch" role="group" [attr.aria-label]="i18n.t('common.period')">
          <button type="button" class="ui-press-toggle" [attr.aria-pressed]="mode() === 'month'" (click)="modeChange.emit('month')">
            {{ i18n.t('common.periodMonth') }}
          </button>
          <button type="button" class="ui-press-toggle" [attr.aria-pressed]="mode() === 'range'" (click)="modeChange.emit('range')">
            {{ i18n.t('common.periodRange') }}
          </button>
        </div>

        @if (mode() === 'month') {
          <app-month-select class="period-selector__month" [value]="month()" [locale]="locale()" [ariaLabel]="i18n.t('common.period')"
            [previousYearLabel]="i18n.t('common.previousYear')" [nextYearLabel]="i18n.t('common.nextYear')" [yearLabel]="i18n.t('common.year')"
            (valueChange)="monthChange.emit($event)" />
        } @else {
          <div class="period-selector__range">
            <label class="field period-selector__range-field">
              <span class="period-selector__visually-hidden">{{ i18n.t('common.from') }}</span>
              <input type="date" [value]="rangeFromDate()" (change)="rangeFromDateChange.emit(dateValue($event))" />
            </label>
            <span class="period-selector__separator" aria-hidden="true">{{ i18n.t('common.to') }}</span>
            <label class="field period-selector__range-field">
              <span class="period-selector__visually-hidden">{{ i18n.t('common.to') }}</span>
              <input type="date" [value]="rangeToDate()" (change)="rangeToDateChange.emit(dateValue($event))" />
            </label>
          </div>
        }
      </div>
    </div>
  `,
  styles: `
    :host {
      display: block;
      min-width: 0;
      container-type: inline-size;
      container-name: period-selector;
    }
    .period-selector {
      min-width: 0;
      display: grid;
      gap: var(--field-gap);
      font-size: var(--control-font-size);
      font-weight: 650;
    }
    .period-selector__label { line-height: var(--control-line-height); }
    .period-selector__row {
      min-width: 0;
      display: flex;
      align-items: flex-start;
      gap: var(--form-gap);
    }
    .period-selector__switch {
      flex: 0 0 auto;
      display: flex;
      align-items: flex-start;
      gap: var(--space-2);
    }
    .period-selector__switch .ui-press-toggle { min-height: var(--control-height); }
    .period-selector__month { flex: 0 1 var(--period-month-select-width); width: var(--period-month-select-width); min-width: 0; }
    .period-selector__range {
      flex: 1 1 auto;
      min-width: 0;
      display: grid;
      grid-template-columns: minmax(var(--period-date-field-min-width), 1fr) auto minmax(var(--period-date-field-min-width), 1fr);
      align-items: center;
      gap: var(--space-2);
    }
    .period-selector__range-field, .period-selector__range-field input { min-width: 0; width: 100%; }
    .period-selector__separator {
      min-height: var(--control-height);
      display: grid;
      place-items: center;
      color: var(--text-muted);
      font-size: var(--control-detail-font-size);
      font-weight: 650;
      white-space: nowrap;
    }
    .period-selector__visually-hidden {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }

    @container period-selector (max-width: 520px) {
      .period-selector__row { display: grid; grid-template-columns: minmax(0, 1fr); }
      .period-selector__switch { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); width: 100%; }
      .period-selector__switch .ui-press-toggle { min-width: 0; }
      .period-selector__month { width: 100%; max-width: none; }
      .period-selector__range { grid-template-columns: minmax(0, 1fr); }
      .period-selector__separator { min-height: auto; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PeriodSelectorComponent {
  readonly i18n = inject(I18nService);
  readonly mode = input.required<PeriodMode>();
  readonly month = input.required<string>();
  readonly rangeFromDate = input('');
  readonly rangeToDate = input('');
  readonly locale = input('pt-BR');

  readonly modeChange = output<PeriodMode>();
  readonly monthChange = output<string>();
  readonly rangeFromDateChange = output<string>();
  readonly rangeToDateChange = output<string>();

  dateValue(event: Event): string {
    return (event.target as HTMLInputElement).value;
  }
}
