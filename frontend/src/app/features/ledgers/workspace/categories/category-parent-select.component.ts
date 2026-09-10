import { ChangeDetectionStrategy, Component, ElementRef, HostListener, computed, inject, input, output, signal } from '@angular/core';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { EntityBadgeComponent } from '../../../../shared/ledger/entity-badge.component';
import { normalizeSearchText } from '../../../../shared/search-normalization';
import { DropdownSearchAutofocusDirective } from '../../../../shared/ui/dropdown-search-autofocus.directive';
import { IconComponent } from '../../../../shared/ui/icon.component';

export const ROOT_CATEGORY_VALUE = '__root__';

@Component({
  selector: 'app-category-parent-select',
  standalone: true,
  imports: [DropdownSearchAutofocusDirective, EntityBadgeComponent, IconComponent],
  template: `
    <div class="parent-select">
      <button type="button" class="parent-select__trigger ui-select-trigger ui-trigger-with-icon" (click)="toggleList()"
        [attr.aria-label]="ariaLabel()" aria-haspopup="listbox" [attr.aria-expanded]="open()" [attr.aria-controls]="listId">
        @if (selectedCategory(); as category) {
          <app-entity-badge [icon]="category.icon" [color]="category.color_code" [size]="30" />
          <span class="parent-select__value">{{ category.name }}</span>
        } @else {
          <span class="parent-select__root-icon ui-icon-badge ui-icon-badge--neutral ui-projected-icon"><app-icon name="folder" [size]="17" /></span>
          <span class="parent-select__value">{{ rootLabel() }}</span>
        }
        <app-icon class="ui-select-chevron" name="chevron-down" [size]="17" />
      </button>

      @if (open()) {
        <div class="parent-select__panel ui-dropdown-panel" [id]="listId">
          <label class="ui-dropdown-search">
            <app-icon name="search" [size]="17" />
            <input type="search" autocomplete="off" [attr.aria-label]="searchPlaceholder() || ariaLabel()"
              [placeholder]="searchPlaceholder()" [value]="query()" (input)="updateQuery($event)"
              (keydown.escape)="closeList()" (keydown.enter)="selectFirst($event)" appDropdownSearchAutofocus />
          </label>

          <div class="parent-select__list" role="listbox">
            @if (rootVisible()) {
              <button type="button" class="ui-menu-option-with-icon" role="option" [attr.aria-selected]="value() === rootValue" (click)="chooseRoot()">
                <span class="parent-select__root-icon ui-icon-badge ui-icon-badge--neutral ui-projected-icon"><app-icon name="folder" [size]="17" /></span>
                <span class="parent-select__option-name">{{ rootLabel() }}</span>
                @if (value() === rootValue) { <app-icon name="check" [size]="16" /> }
              </button>
            }
            @for (category of filteredCategories(); track category.uuid) {
              <button type="button" class="ui-menu-option-with-icon" role="option" [attr.aria-selected]="value() === category.uuid" (click)="choose(category.uuid)">
                <app-entity-badge [icon]="category.icon" [color]="category.color_code" [size]="30" />
                <span class="parent-select__option-name">{{ category.name }}</span>
                @if (value() === category.uuid) { <app-icon name="check" [size]="16" /> }
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
    :host { display: block; min-width: 0; }
    .parent-select { position: relative; }
    .parent-select__trigger {
      width: 100%;
      height: var(--control-height);
      text-align: left;
    }
    .parent-select__trigger[aria-expanded='true'] {
      border-color: var(--blue-strong);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--blue) 32%, transparent);
    }
    .parent-select .ui-dropdown-search:focus-within { border-color: var(--blue-strong); box-shadow: 0 0 0 3px color-mix(in srgb, var(--blue) 32%, transparent); }
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

  @HostListener('document:mousedown', ['$event'])
  closeWhenClickingOutside(event: MouseEvent): void {
    if (!this.host.nativeElement.contains(event.target as Node)) this.closeList();
  }

  @HostListener('document:keydown.escape')
  closeOnEscape(): void {
    this.closeList();
  }

  toggleList(): void {
    this.open() ? this.closeList() : this.openList();
  }

  openList(): void {
    this.query.set('');
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
    if (this.rootVisible()) {
      event.preventDefault();
      this.chooseRoot();
      return;
    }
    const first = this.filteredCategories()[0];
    if (!first) return;
    event.preventDefault();
    this.choose(first.uuid);
  }

  chooseRoot(): void {
    this.choose(ROOT_CATEGORY_VALUE);
  }

  choose(value: string): void {
    this.open.set(false);
    this.query.set('');
    this.valueChange.emit(value);
  }
}
