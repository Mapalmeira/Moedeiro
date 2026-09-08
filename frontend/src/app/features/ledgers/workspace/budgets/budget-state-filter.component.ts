import { ChangeDetectionStrategy, Component, ElementRef, HostListener, computed, inject, input, output, signal } from '@angular/core';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerBudgetState } from '../../../../core/ledgers/ledger-budgets.models';
import { ENTITY_BADGE_DEFAULT_SYMBOL_SIZE } from '../../../../shared/ledger/entity-badge.component';
import { IconComponent } from '../../../../shared/ui/icon.component';

const ALL_STATES: readonly LedgerBudgetState[] = ['ACTIVE', 'FUTURE', 'FINISHED'];

@Component({
  selector: 'app-budget-state-filter',
  standalone: true,
  imports: [IconComponent],
  template: `
    <div class="state-filter">
      <button type="button" class="state-filter__trigger ui-select-trigger ui-trigger-with-icon" (click)="toggle()"
        [attr.aria-expanded]="open()" [attr.aria-label]="i18n.t('budgets.filterState')">
        <span class="state-filter__icon ui-icon-badge ui-icon-badge--neutral ui-projected-icon" aria-hidden="true"><app-icon name="wallet" [size]="triggerIconSize" /></span>
        <span class="ui-trigger-content"><strong class="ui-trigger-value">{{ triggerLabel() }}</strong></span>
        <app-icon class="ui-select-chevron" name="chevron-down" [size]="17" />
      </button>
      @if (open()) {
        <div class="state-filter__panel ui-dropdown-panel">
          @for (state of states; track state) {
            <button type="button" class="state-filter__option" role="checkbox" [attr.aria-checked]="isSelected(state)" (click)="toggleState(state)">
              <span class="state-filter__check ui-icon-badge" [class.state-filter__check--selected]="isSelected(state)" aria-hidden="true">
                @if (isSelected(state)) { <app-icon name="check" [size]="14" /> }
              </span>
              <span>{{ label(state) }}</span>
            </button>
          }
        </div>
      }
    </div>
  `,
  styles: `
    :host { display: block; min-width: 0; }
    .state-filter { position: relative; min-width: 0; }
    .state-filter__trigger {
      width: 100%; height: var(--control-height); padding-block: 0; text-align: left;
    }
    .state-filter__trigger[aria-expanded='true'] { border-color: var(--yellow-strong); box-shadow: 0 0 0 3px color-mix(in srgb, var(--yellow) 32%, transparent); }
    .state-filter__panel { position: absolute; z-index: var(--layer-dropdown); top: calc(100% + var(--space-2)); left: 0; right: 0; min-width: max-content; }
    .state-filter__option {
      width: 100%; min-height: var(--menu-item-height); display: grid; grid-template-columns: var(--inline-icon-size) minmax(0, 1fr); align-items: center; gap: var(--space-3);
      padding: var(--space-2) var(--space-3); border: 0; border-radius: var(--radius-sm); background: transparent; color: var(--text); text-align: left;
      font-size: var(--control-font-size); font-weight: var(--control-font-weight);
    }
    .state-filter__option:hover { background: var(--surface-muted); }
    .state-filter__check { --icon-badge-size: var(--inline-icon-size); border-color: var(--line); background: var(--surface); }
    .state-filter__check--selected { border-color: var(--line-strong); background: var(--yellow); color: var(--on-yellow); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BudgetStateFilterComponent {
  readonly triggerIconSize = ENTITY_BADGE_DEFAULT_SYMBOL_SIZE;
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  readonly i18n = inject(I18nService);
  readonly selected = input.required<readonly LedgerBudgetState[]>();
  readonly selectedChange = output<readonly LedgerBudgetState[]>();
  readonly open = signal(false);
  readonly states = ALL_STATES;
  readonly triggerLabel = computed(() => {
    const values = this.selected();
    if (values.length === ALL_STATES.length) return this.i18n.t('budgets.states.all');
    if (values.length === 1) return this.label(values[0]);
    return this.i18n.t('budgets.states.count', { count: values.length });
  });

  @HostListener('document:mousedown', ['$event'])
  closeOutside(event: MouseEvent): void {
    if (this.open() && !this.host.nativeElement.contains(event.target as Node)) this.open.set(false);
  }

  @HostListener('document:keydown.escape')
  closeEscape(): void { this.open.set(false); }

  toggle(): void { this.open.update(value => !value); }

  isSelected(state: LedgerBudgetState): boolean { return this.selected().includes(state); }

  toggleState(state: LedgerBudgetState): void {
    const current = new Set(this.selected());
    current.has(state) ? current.delete(state) : current.add(state);
    if (!current.size) return;
    this.selectedChange.emit(ALL_STATES.filter(value => current.has(value)));
  }

  label(state: LedgerBudgetState): string {
    return this.i18n.t(state === 'ACTIVE' ? 'budgets.states.active' : state === 'FUTURE' ? 'budgets.states.future' : 'budgets.states.finished');
  }
}
