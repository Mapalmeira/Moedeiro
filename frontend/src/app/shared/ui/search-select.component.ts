import { ChangeDetectionStrategy, Component, ElementRef, HostListener, computed, inject, input, output, signal } from '@angular/core';
import { normalizeSearchText } from '../search-normalization';
import { DropdownSearchAutofocusDirective } from './dropdown-search-autofocus.directive';
import { IconComponent } from './icon.component';

@Component({
  selector: 'app-search-select',
  standalone: true,
  imports: [DropdownSearchAutofocusDirective, IconComponent],
  template: `
    <div class="search-select" [class.search-select--up]="openDirection() === 'up'">
      <button type="button" class="search-select__trigger ui-select-trigger" (click)="toggleList()"
        [attr.aria-label]="ariaLabel()" [attr.aria-expanded]="open()" [attr.aria-controls]="listId">
        <span class="search-select__value">{{ value() }}</span>
        <app-icon class="ui-select-chevron" name="chevron-down" [size]="17" />
      </button>

      @if (open()) {
        <div class="search-select__panel ui-dropdown-panel" [id]="listId">
          <label class="ui-dropdown-search">
            <app-icon name="search" [size]="17" />
            <input
              type="search"
              autocomplete="off"
              [attr.aria-label]="searchPlaceholder() || ariaLabel()"
              [placeholder]="searchPlaceholder()"
              [value]="query()"
              (input)="updateQuery($event)"
              (keydown.escape)="closeList()"
              (keydown.enter)="selectFirst($event)"
              appDropdownSearchAutofocus />
          </label>

          <div class="search-select__list" role="listbox">
            @for (option of filteredOptions(); track option) {
              <button type="button" role="option" [attr.aria-selected]="option === value()" (click)="choose(option)">
                <span>{{ option }}</span>
                @if (option === value()) { <app-icon name="check" [size]="16" /> }
              </button>
            } @empty {
              <div class="search-select__empty">{{ emptyText() }}</div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: `
    :host { display: block; min-width: 0; }
    .search-select { position: relative; }
    .search-select__trigger {
      width: 100%;
      height: var(--control-height);
      display: grid;
      grid-template-columns: minmax(0, 1fr) 17px;
      align-items: center;
      gap: var(--space-3);
      padding: 0 var(--space-3);
      text-align: left;
    }
    .search-select__value { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .search-select__panel { position: absolute; z-index: var(--layer-dropdown); top: calc(100% + var(--space-2)); left: 0; right: 0; }
    .search-select--up .search-select__panel { top: auto; bottom: calc(100% + var(--space-2)); }
    .search-select__list { max-height: min(190px, 28dvh); overflow-y: auto; overscroll-behavior: contain; display: grid; gap: var(--space-1); }
    .search-select__list button {
      width: 100%;
      min-height: var(--menu-item-height);
      display: grid;
      grid-template-columns: minmax(0, 1fr) 20px;
      align-items: center;
      gap: var(--space-2);
      padding: var(--space-2) var(--space-3);
      border: 0;
      border-radius: var(--radius-sm);
      background: transparent;
      color: var(--text);
      text-align: left;
      font-size: var(--control-font-size);
      font-weight: 650;
      line-height: var(--control-line-height);
    }
    .search-select__list button:not([aria-selected='true']):hover { background: var(--surface-muted); }
    .search-select__list button[aria-selected='true'],
    .search-select__list button[aria-selected='true']:hover { background: var(--green-soft); }
    .search-select__list button span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .search-select__empty { padding: var(--space-3); color: var(--text-muted); font-size: .88rem; text-align: center; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchSelectComponent {
  private static nextId = 0;
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly options = input.required<readonly string[]>();
  readonly value = input('');
  readonly ariaLabel = input('');
  readonly searchPlaceholder = input('');
  readonly emptyText = input('No results');
  readonly openDirection = input<'up' | 'down'>('down');
  readonly valueChange = output<string>();

  readonly open = signal(false);
  readonly query = signal('');
  readonly listId = `search-select-${SearchSelectComponent.nextId++}`;

  readonly filteredOptions = computed(() => {
    const needle = normalizeSearchText(this.query().trim());
    if (!needle) return this.options();
    return this.options().filter((option) => normalizeSearchText(option).includes(needle));
  });

  @HostListener('document:mousedown', ['$event'])
  closeWhenClickingOutside(event: MouseEvent): void {
    if (!this.host.nativeElement.contains(event.target as Node)) this.closeList();
  }

  @HostListener('document:keydown.escape')
  closeOnEscape(): void {
    this.closeList();
  }

  openList(): void {
    this.query.set('');
    this.open.set(true);
  }

  toggleList(): void {
    this.open() ? this.closeList() : this.openList();
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
    this.choose(first);
  }

  choose(option: string): void {
    this.open.set(false);
    this.query.set('');
    this.valueChange.emit(option);
  }
}
