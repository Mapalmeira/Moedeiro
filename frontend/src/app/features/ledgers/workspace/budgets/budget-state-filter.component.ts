import { ChangeDetectionStrategy, Component, computed, inject, input, output, signal } from '@angular/core';
import { DismissiblePopoverDirective } from '../../../../shared/ui/dismissible-popover.directive';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerBudgetState } from '../../../../core/ledgers/ledger-budgets.models';
import { IconComponent } from '../../../../shared/ui/icon.component';
import { isListboxNavigationKey, nextListboxIndex } from '../../../../shared/ui/listbox-navigation';

const ALL_STATES: readonly LedgerBudgetState[] = ['ACTIVE', 'FUTURE', 'FINISHED'];

@Component({
  selector: 'app-budget-state-filter',
  standalone: true,
  imports: [DismissiblePopoverDirective, IconComponent],
  template: `
    <div class="state-filter" [appDismissiblePopover]="open()" (dismiss)="closeList()">
      <button type="button" class="state-filter__trigger ui-select-trigger ui-trigger-with-icon" (click)="toggle()"
        aria-haspopup="listbox" [attr.aria-expanded]="open()" [attr.aria-controls]="listId" [attr.aria-activedescendant]="open() ? activeOptionId() : null"
        [attr.aria-label]="i18n.t('budgets.filterState')" (keydown)="handleKeydown($event)">
        <span class="state-filter__icon ui-icon-badge ui-icon-badge--neutral ui-projected-icon" aria-hidden="true"><app-icon name="LucideWallet" size="badge" /></span>
        <span class="ui-trigger-content"><strong class="ui-trigger-value ui-truncate">{{ triggerLabel() }}</strong></span>
        <app-icon class="ui-select-chevron" name="LucideChevronDown" size="compact" />
      </button>
      @if (open()) {
        <div class="state-filter__panel ui-dropdown-panel" role="listbox" aria-multiselectable="true" [id]="listId">
          @for (state of states; track state; let stateIndex = $index) {
            <button type="button" class="state-filter__option" role="option" [id]="optionId(stateIndex)" tabindex="-1"
              [attr.aria-selected]="isSelected(state)" (click)="toggleState(state)">
              <span class="state-filter__check ui-icon-badge" [class.state-filter__check--selected]="isSelected(state)" aria-hidden="true">
                @if (isSelected(state)) { <app-icon name="LucideCheck" size="indicator" /> }
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
  private static nextId = 0;
  readonly i18n = inject(I18nService);
  readonly selected = input.required<readonly LedgerBudgetState[]>();
  readonly selectedChange = output<readonly LedgerBudgetState[]>();
  readonly open = signal(false);
  readonly activeIndex = signal(-1);
  readonly listId = `budget-state-filter-${BudgetStateFilterComponent.nextId++}`;
  readonly activeOptionId = () => this.activeIndex() >= 0 ? this.optionId(this.activeIndex()) : null;
  readonly states = ALL_STATES;
  readonly triggerLabel = computed(() => {
    const values = this.selected();
    if (values.length === ALL_STATES.length) return this.i18n.t('budgets.states.all');
    if (values.length === 1) return this.label(values[0]);
    return this.i18n.t('budgets.states.count', { count: values.length });
  });

  toggle(): void {
    if (this.open()) this.closeList();
    else { this.open.set(true); this.activeIndex.set(0); }
  }

  closeList(): void { this.open.set(false); this.activeIndex.set(-1); }

  handleKeydown(event: KeyboardEvent): void {
    if (isListboxNavigationKey(event.key)) {
      event.preventDefault();
      if (!this.open()) { this.open.set(true); this.activeIndex.set(event.key === 'ArrowUp' || event.key === 'End' ? this.states.length - 1 : 0); }
      else this.activeIndex.set(nextListboxIndex(this.activeIndex(), this.states.length, event.key));
      return;
    }
    if (this.open() && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      const state = this.states[this.activeIndex()];
      if (state) this.toggleState(state);
    }
  }

  optionId(index: number): string { return `${this.listId}-option-${index}`; }

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
