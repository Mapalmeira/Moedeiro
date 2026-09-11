import { ChangeDetectionStrategy, Component, ElementRef, Injector, afterNextRender, computed, inject, input, output, signal } from '@angular/core';
import { DismissiblePopoverDirective } from '../../../../shared/ui/dismissible-popover.directive';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { EntityBadgeComponent } from '../../../../shared/ledger/entity-badge.component';
import { normalizeSearchText } from '../../../../shared/search-normalization';
import { DropdownSearchAutofocusDirective } from '../../../../shared/ui/dropdown-search-autofocus.directive';
import { IconComponent } from '../../../../shared/ui/icon.component';
import { isListboxNavigationKey, nextListboxIndex } from '../../../../shared/ui/listbox-navigation';

export const ROOT_CATEGORY_VALUE = '__root__';

@Component({
  selector: 'app-category-parent-select',
  standalone: true,
  imports: [DismissiblePopoverDirective, DropdownSearchAutofocusDirective, EntityBadgeComponent, IconComponent],
  template: `
    <div class="parent-select" [appDismissiblePopover]="open()" (dismiss)="closeList()">
      <button type="button" class="parent-select__trigger ui-select-trigger ui-trigger-with-icon" (click)="toggleList()"
        [attr.aria-label]="ariaLabel()" aria-haspopup="listbox" [attr.aria-expanded]="open()" [attr.aria-controls]="listId"
        (keydown)="handleTriggerKeydown($event)">
        @if (selectedCategory(); as category) {
          <app-entity-badge [icon]="category.icon" [color]="category.color_code" [size]="30" />
          <span class="parent-select__value">{{ category.name }}</span>
        } @else {
          <span class="parent-select__root-icon ui-icon-badge ui-icon-badge--neutral ui-projected-icon"><app-icon name="LucideFolder" size="control" /></span>
          <span class="parent-select__value">{{ rootLabel() }}</span>
        }
        <app-icon class="ui-select-chevron" name="LucideChevronDown" size="compact" />
      </button>

      @if (open()) {
        <div class="parent-select__panel ui-dropdown-panel">
          <label class="ui-dropdown-search">
            <app-icon name="LucideSearch" size="control" />
            <input type="search" role="combobox" autocomplete="off" [attr.aria-label]="searchPlaceholder() || ariaLabel()"
              aria-autocomplete="list" [attr.aria-expanded]="open()" [attr.aria-controls]="listId" [attr.aria-activedescendant]="activeOptionId()"
              [placeholder]="searchPlaceholder()" [value]="query()" (input)="updateQuery($event)"
              (keydown)="handleSearchKeydown($event)" appDropdownSearchAutofocus />
          </label>

          <div class="parent-select__list" role="listbox" [id]="listId">
            @if (rootVisible()) {
              <button type="button" class="ui-menu-option-with-icon" role="option" [id]="optionId(0)" tabindex="-1" [attr.aria-selected]="value() === rootValue" (click)="chooseRoot()">
                <span class="parent-select__root-icon ui-icon-badge ui-icon-badge--neutral ui-projected-icon"><app-icon name="LucideFolder" size="control" /></span>
                <span class="parent-select__option-name">{{ rootLabel() }}</span>
                @if (value() === rootValue) { <app-icon name="LucideCheck" size="compact" /> }
              </button>
            }
            @for (category of filteredCategories(); track category.uuid; let categoryIndex = $index) {
              <button type="button" class="ui-menu-option-with-icon" role="option" [id]="optionId(categoryIndex + (rootVisible() ? 1 : 0))" tabindex="-1"
                [attr.aria-selected]="value() === category.uuid" (click)="choose(category.uuid)">
                <app-entity-badge [icon]="category.icon" [color]="category.color_code" [size]="30" />
                <span class="parent-select__option-name">{{ category.name }}</span>
                @if (value() === category.uuid) { <app-icon name="LucideCheck" size="compact" /> }
              </button>
            }
            @if (!rootVisible() && filteredCategories().length === 0) {
              <div class="parent-select__empty">{{ emptyText() }}</div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: `
    :host { --ui-accent: var(--blue); --ui-accent-strong: var(--blue-strong); display: block; min-width: 0; }
    .parent-select { position: relative; }
    .parent-select__trigger {
      width: 100%;
      height: var(--control-height);
      text-align: left;
    }
    .parent-select__value, .parent-select__option-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .parent-select__panel { position: absolute; z-index: var(--layer-dropdown); top: calc(100% + var(--space-2)); left: 0; right: 0; }
    .parent-select__list { max-height: min(240px, 32dvh); overflow-y: auto; overscroll-behavior: contain; display: grid; gap: var(--space-1); }
    .parent-select__list button {
      width: 100%;
      min-height: var(--menu-item-height);
      border: 0;
      border-radius: var(--radius-sm);
      background: transparent;
      color: var(--text);
      text-align: left;
      font-size: var(--control-font-size);
      font-weight: var(--control-font-weight);
      line-height: var(--control-line-height);
    }
    .parent-select__list button:not([aria-selected='true']):hover { background: var(--surface-muted); }
    .parent-select__list button[aria-selected='true'], .parent-select__list button[aria-selected='true']:hover { background: var(--blue-soft); }
    .parent-select__empty { padding: var(--space-3); color: var(--text-muted); font-size: var(--control-font-size); text-align: center; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CategoryParentSelectComponent {
  private static nextId = 0;
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly injector = inject(Injector);

  readonly categories = input.required<readonly LedgerCategory[]>();
  readonly excludedUuids = input<ReadonlySet<string>>(new Set<string>());
  readonly value = input(ROOT_CATEGORY_VALUE);
  readonly ariaLabel = input('');
  readonly rootLabel = input('Root');
  readonly searchPlaceholder = input('');
  readonly emptyText = input('No results');
  readonly valueChange = output<string>();

  readonly rootValue = ROOT_CATEGORY_VALUE;
  readonly open = signal(false);
  readonly query = signal('');
  readonly activeIndex = signal(-1);
  readonly listId = `category-parent-select-${CategoryParentSelectComponent.nextId++}`;

  readonly availableCategories = computed(() => {
    const excluded = this.excludedUuids();
    return this.categories().filter(category => !excluded.has(category.uuid));
  });
  readonly filteredCategories = computed(() => {
    const needle = normalizeSearchText(this.query().trim());
    if (!needle) return this.availableCategories();
    return this.availableCategories().filter(category => normalizeSearchText(category.name).includes(needle));
  });
  readonly rootVisible = computed(() => {
    const needle = normalizeSearchText(this.query().trim());
    return !needle || normalizeSearchText(this.rootLabel()).includes(needle);
  });
  readonly selectedCategory = computed(() => this.categories().find(category => category.uuid === this.value()) ?? null);
  readonly visibleValues = computed(() => [
    ...(this.rootVisible() ? [ROOT_CATEGORY_VALUE] : []),
    ...this.filteredCategories().map(category => category.uuid),
  ]);
  readonly activeOptionId = computed(() => this.activeIndex() >= 0 ? this.optionId(this.activeIndex()) : null);

  toggleList(): void {
    this.open() ? this.closeList() : this.openList();
  }

  openList(): void {
    this.query.set('');
    this.open.set(true);
    this.syncActiveIndex();
  }

  closeList(): void {
    this.open.set(false);
    this.query.set('');
    this.activeIndex.set(-1);
  }

  updateQuery(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
    this.syncActiveIndex();
  }

  handleTriggerKeydown(event: KeyboardEvent): void {
    if (!isListboxNavigationKey(event.key)) return;
    event.preventDefault();
    if (!this.open()) this.openList();
    else this.moveActive(event.key);
  }

  handleSearchKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      event.preventDefault();
      this.closeList();
      return;
    }
    if (isListboxNavigationKey(event.key)) {
      event.preventDefault();
      this.moveActive(event.key);
      return;
    }
    if (event.key === 'Enter') {
      const value = this.visibleValues()[this.activeIndex()];
      if (!value) return;
      event.preventDefault();
      this.choose(value);
    }
  }

  optionId(index: number): string { return `${this.listId}-option-${index}`; }

  private syncActiveIndex(): void {
    const values = this.visibleValues();
    if (!values.length) {
      this.activeIndex.set(-1);
      return;
    }
    const selectedIndex = values.indexOf(this.value());
    this.activeIndex.set(selectedIndex >= 0 ? selectedIndex : 0);
    this.scrollActiveOption();
  }

  private moveActive(key: 'ArrowDown' | 'ArrowUp' | 'Home' | 'End'): void {
    const next = nextListboxIndex(this.activeIndex(), this.visibleValues().length, key);
    this.activeIndex.set(next);
    this.scrollActiveOption();
  }

  private scrollActiveOption(): void {
    const id = this.activeOptionId();
    if (!id) return;
    afterNextRender(() => {
      this.host.nativeElement.ownerDocument.getElementById(id)?.scrollIntoView?.({ block: 'nearest' });
    }, { injector: this.injector });
  }

  chooseRoot(): void {
    this.choose(ROOT_CATEGORY_VALUE);
  }

  choose(value: string): void {
    this.open.set(false);
    this.query.set('');
    this.activeIndex.set(-1);
    this.valueChange.emit(value);
  }
}
