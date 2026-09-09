import { ChangeDetectionStrategy, Component, ElementRef, HostListener, computed, inject, input, output, signal } from '@angular/core';
import { ENTITY_BADGE_DEFAULT_SYMBOL_SIZE, EntityBadgeComponent } from './entity-badge.component';
import { DropdownSearchAutofocusDirective } from '../ui/dropdown-search-autofocus.directive';
import { IconComponent, IconName } from '../ui/icon.component';

export type EntitySearchOptionTone = 'green' | 'yellow' | 'blue' | 'neutral';

export interface EntitySearchOption {
  value: string;
  label: string;
  detail?: string | null;
  icon?: string;
  color?: string;
  uiIcon?: IconName;
  tone?: EntitySearchOptionTone;
}

@Component({
  selector: 'app-entity-search-select',
  standalone: true,
  imports: [DropdownSearchAutofocusDirective, EntityBadgeComponent, IconComponent],
  template: `
    <div class="entity-search-select" [class.entity-search-select--up]="opensUp()">
      <button type="button" class="entity-search-select__trigger ui-select-trigger" (click)="toggleList()"
        [disabled]="disabled()" [attr.aria-label]="ariaLabel()" aria-haspopup="listbox" [attr.aria-expanded]="open()" [attr.aria-controls]="listId">
        @if (selectedOption(); as option) {
          @if (option.icon && option.color) {
            <app-entity-badge [icon]="option.icon" [color]="option.color" />
          } @else if (option.uiIcon) {
            <span class="entity-search-select__option-icon ui-icon-badge ui-projected-icon"
              [class.ui-icon-badge--green]="option.tone === 'green'"
              [class.ui-icon-badge--yellow]="option.tone === 'yellow'"
              [class.ui-icon-badge--blue]="option.tone === 'blue'"
              [class.ui-icon-badge--neutral]="!option.tone || option.tone === 'neutral'">
              <app-icon [name]="option.uiIcon" [size]="optionIconSize" />
            </span>
          }
          <span class="entity-search-select__copy">
            <strong>{{ option.label }}</strong>
            @if (option.detail) { <small>{{ option.detail }}</small> }
          </span>
        } @else {
          <span class="entity-search-select__empty-value">{{ emptyValueText() }}</span>
        }
        <app-icon class="ui-select-chevron" name="chevron-down" [size]="17" />
      </button>

      @if (open()) {
        <div class="entity-search-select__panel ui-dropdown-panel" [class.entity-search-select__panel--searchable]="searchable()" [id]="listId"
          [style.--entity-search-available-height]="availableHeight() + 'px'">
          @if (searchable()) {
            <label class="ui-dropdown-search">
              <app-icon name="search" [size]="17" />
              <input type="search" autocomplete="off" [attr.aria-label]="searchPlaceholder() || ariaLabel()"
                [placeholder]="searchPlaceholder()" [value]="query()" (input)="updateQuery($event)"
                (keydown.escape)="closeList()" (keydown.enter)="selectFirst($event)" appDropdownSearchAutofocus />
            </label>
          }

          <div class="entity-search-select__list" role="listbox">
            @for (option of filteredOptions(); track option.value) {
              <button type="button" role="option" [attr.aria-selected]="value() === option.value" (click)="choose(option.value)">
                @if (option.icon && option.color) {
                  <app-entity-badge [icon]="option.icon" [color]="option.color" />
                } @else if (option.uiIcon) {
                  <span class="entity-search-select__option-icon ui-icon-badge ui-projected-icon"
                    [class.ui-icon-badge--green]="option.tone === 'green'"
                    [class.ui-icon-badge--yellow]="option.tone === 'yellow'"
                    [class.ui-icon-badge--blue]="option.tone === 'blue'"
                    [class.ui-icon-badge--neutral]="!option.tone || option.tone === 'neutral'">
                    <app-icon [name]="option.uiIcon" [size]="optionIconSize" />
                  </span>
                }
                <span class="entity-search-select__copy">
                  <strong>{{ option.label }}</strong>
                  @if (option.detail) { <small>{{ option.detail }}</small> }
                </span>
                @if (value() === option.value) { <app-icon name="check" [size]="16" /> }
              </button>
            } @empty {
              <div class="entity-search-select__empty">{{ emptyText() }}</div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: `
    :host { display: block; min-width: 0; }
    .entity-search-select { position: relative; min-width: 0; }
    .entity-search-select__trigger {
      width: 100%;
      height: var(--control-height);
      display: grid;
      grid-template-columns: var(--control-icon-footprint) minmax(0, 1fr) var(--chevron-track-size);
      align-items: center;
      gap: var(--space-2);
      padding: 0 var(--control-padding-inline) 0 var(--space-2);
      text-align: left;
    }
    .entity-search-select__trigger[aria-expanded='true'] {
      border-color: var(--entity-select-accent-strong, var(--green-strong));
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--entity-select-accent, var(--green)) 32%, transparent);
    }
    .entity-search-select__copy { min-width: 0; display: grid; gap: var(--space-1); }
    .entity-search-select__copy strong,
    .entity-search-select__copy small,
    .entity-search-select__empty-value { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .entity-search-select__copy strong { font: inherit; font-weight: var(--control-font-weight); }
    .entity-search-select__copy small { color: var(--text-muted); font-size: var(--control-detail-font-size); font-weight: 650; }
    .entity-search-select__empty-value { grid-column: 1 / span 2; color: var(--text-muted); }
    .entity-search-select__panel {
      position: absolute;
      z-index: var(--layer-dropdown);
      top: calc(100% + var(--space-2));
      left: 0;
      right: 0;
      max-height: min(var(--search-dropdown-max-height), max(0px, calc(var(--entity-search-available-height, 100dvh) - var(--space-2))));
      grid-template-rows: minmax(0, 1fr);
      overflow: hidden;
    }
    .entity-search-select__panel--searchable { grid-template-rows: auto minmax(0, 1fr); }
    .entity-search-select--up .entity-search-select__panel { top: auto; bottom: calc(100% + var(--space-2)); }
    .entity-search-select__list { min-height: 0; overflow-y: auto; overscroll-behavior: contain; display: grid; align-content: start; gap: var(--space-1); }
    .entity-search-select__list button {
      width: 100%;
      min-height: var(--menu-item-height);
      display: grid;
      grid-template-columns: var(--control-icon-footprint) minmax(0, 1fr) var(--inline-icon-size);
      align-items: center;
      gap: var(--space-2);
      padding: var(--space-2) var(--space-3) var(--space-2) var(--space-2);
      border: 0;
      border-radius: var(--radius-sm);
      background: transparent;
      color: var(--text);
      text-align: left;
      font-size: var(--control-font-size);
      line-height: var(--control-line-height);
    }
    .entity-search-select__list button:not([aria-selected='true']):hover { background: var(--surface-muted); }
    .entity-search-select__list button[aria-selected='true'],
    .entity-search-select__list button[aria-selected='true']:hover { background: var(--entity-select-selected-background, var(--green-soft)); }
    .entity-search-select__empty { padding: var(--space-3); color: var(--text-muted); font-size: var(--control-font-size); text-align: center; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntitySearchSelectComponent {
  readonly optionIconSize = ENTITY_BADGE_DEFAULT_SYMBOL_SIZE;
  private static nextId = 0;
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly options = input.required<readonly EntitySearchOption[]>();
  readonly value = input('');
  readonly ariaLabel = input('');
  readonly searchPlaceholder = input('');
  readonly emptyText = input('No results');
  readonly emptyValueText = input('—');
  readonly searchable = input(true);
  readonly disabled = input(false);
  readonly openDirection = input<'auto' | 'up' | 'down'>('auto');
  readonly valueChange = output<string>();

  readonly open = signal(false);
  readonly query = signal('');
  readonly opensUp = signal(false);
  readonly availableHeight = signal(0);
  readonly listId = `entity-search-select-${EntitySearchSelectComponent.nextId++}`;
  private readonly optionIndex = computed(() => new Map(this.options().map(option => [option.value, option] as const)));
  private readonly searchableOptions = computed(() => this.options().map(option => ({
    option,
    searchText: `${option.label} ${option.detail ?? ''}`.toLocaleLowerCase(),
  })));
  readonly selectedOption = computed(() => this.optionIndex().get(this.value()) ?? null);
  readonly filteredOptions = computed(() => {
    const needle = this.query().trim().toLocaleLowerCase();
    if (!needle || !this.searchable()) return this.options();
    return this.searchableOptions().filter(entry => entry.searchText.includes(needle)).map(entry => entry.option);
  });

  @HostListener('document:mousedown', ['$event'])
  closeWhenClickingOutside(event: MouseEvent): void {
    if (!this.open() || this.host.nativeElement.contains(event.target as Node)) return;
    this.closeList();
  }

  @HostListener('document:keydown.escape')
  closeOnEscape(): void {
    if (this.open()) this.closeList();
  }

  @HostListener('window:resize')
  repositionOnResize(): void {
    if (this.open()) this.resolvePanelGeometry();
  }

  toggleList(): void {
    if (this.disabled()) return;
    this.open() ? this.closeList() : this.openList();
  }

  openList(): void {
    this.query.set('');
    this.resolvePanelGeometry();
    this.open.set(true);
  }

  closeList(): void {
    this.open.set(false);
    this.query.set('');
  }

  updateQuery(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
  }

  selectFirst(event: Event): void {
    const first = this.filteredOptions()[0];
    if (!first) return;
    event.preventDefault();
    this.choose(first.value);
  }

  choose(value: string): void {
    this.open.set(false);
    this.query.set('');
    this.valueChange.emit(value);
  }

  private resolvePanelGeometry(): void {
    if (typeof window === 'undefined') return;
    const trigger = this.host.nativeElement.querySelector<HTMLElement>('.entity-search-select__trigger');
    if (!trigger) return;

    const triggerBounds = trigger.getBoundingClientRect();
    const dialog = this.host.nativeElement.closest<HTMLElement>('.ui-dialog-surface');
    const dialogBounds = dialog?.getBoundingClientRect();
    const topBoundary = Math.max(0, dialogBounds?.top ?? 0);
    const bottomBoundary = Math.min(window.innerHeight, dialogBounds?.bottom ?? window.innerHeight);
    const spaceAbove = Math.max(0, triggerBounds.top - topBoundary);
    const spaceBelow = Math.max(0, bottomBoundary - triggerBounds.bottom);
    const direction = this.openDirection();
    const opensUp = direction === 'up' || (direction === 'auto' && spaceAbove > spaceBelow);

    this.opensUp.set(opensUp);
    this.availableHeight.set(opensUp ? spaceAbove : spaceBelow);
  }
}
