import { ChangeDetectionStrategy, Component, ElementRef, HostListener, computed, effect, inject, input, output, signal } from '@angular/core';
import { IconComponent } from './icon.component';

@Component({
  selector: 'app-search-select',
  standalone: true,
  imports: [IconComponent],
  template: `
    <div class="search-select" [class.search-select--open]="open()" [class.search-select--up]="openDirection() === 'up'">
      <div class="search-select__input-wrap">
        <app-icon name="search" [size]="17" />
        <input
          type="search"
          role="combobox"
          autocomplete="off"
          [attr.aria-label]="ariaLabel()"
          [attr.aria-expanded]="open()"
          [attr.aria-controls]="listId"
          [value]="query()"
          (focus)="openList()"
          (input)="updateQuery($event)"
          (keydown.escape)="closeList()"
          (keydown.enter)="selectFirst($event)" />
        <button type="button" class="search-select__chevron" tabindex="-1" (click)="toggleList()" aria-hidden="true">
          <app-icon name="chevron-down" [size]="17" />
        </button>
      </div>

      @if (open()) {
        <div class="search-select__list" role="listbox" [id]="listId">
          @for (option of filteredOptions(); track option) {
            <button type="button" role="option" [attr.aria-selected]="option === value()" (click)="choose(option)">
              <span>{{ option }}</span>
              @if (option === value()) { <app-icon name="check" [size]="16" /> }
            </button>
          } @empty {
            <div class="search-select__empty">{{ emptyText() }}</div>
          }
        </div>
      }
    </div>
  `,
  styles: `
    :host { display: block; min-width: 0; }
    .search-select { position: relative; }
    .search-select__input-wrap { position: relative; display: flex; align-items: center; min-height: 46px; border: 2px solid var(--line-strong); border-radius: var(--radius-sm); background: var(--surface); color: var(--text); transition: box-shadow .12s ease, border-color .12s ease; }
    .search-select--open .search-select__input-wrap:focus-within { border-color: var(--green-strong); box-shadow: 0 0 0 3px color-mix(in srgb, var(--green) 32%, transparent); }
    .search-select__input-wrap > app-icon { position: absolute; left: 12px; color: var(--text-muted); pointer-events: none; }
    input { width: 100%; height: 42px; padding: 0 42px 0 39px; border: 0; outline: 0; background: transparent; color: var(--text); font: inherit; font-weight: 500; }
    input::-webkit-search-cancel-button { display: none; }
    .search-select__chevron { position: absolute; right: 4px; display: grid; place-items: center; width: 34px; height: 34px; padding: 0; border: 0; border-radius: 4px; background: transparent; color: var(--text); }
    .search-select__list { position: absolute; z-index: 60; top: calc(100% + 7px); left: 0; right: 0; max-height: min(178px, 28dvh); overflow-y: auto; overscroll-behavior: contain; padding: 5px; border: 2px solid var(--line-strong); border-radius: 6px; background: var(--surface); box-shadow: 4px 4px 0 var(--shadow-color); }
    .search-select--up .search-select__list { top: auto; bottom: calc(100% + 7px); }
    .search-select__list button { width: 100%; min-height: 36px; display: grid; grid-template-columns: minmax(0, 1fr) 20px; align-items: center; gap: 8px; padding: 7px 9px; border: 0; border-radius: 4px; background: transparent; color: var(--text); text-align: left; font: inherit; font-size: .88rem; }
    .search-select__list button:hover, .search-select__list button[aria-selected='true'] { background: var(--green-soft); }
    .search-select__list button span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .search-select__empty { padding: 12px 10px; color: var(--text-muted); font-size: .88rem; text-align: center; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchSelectComponent {
  private static nextId = 0;
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly options = input.required<readonly string[]>();
  readonly value = input('');
  readonly ariaLabel = input('');
  readonly emptyText = input('No results');
  readonly openDirection = input<'up' | 'down'>('down');
  readonly valueChange = output<string>();

  readonly open = signal(false);
  readonly query = signal('');
  readonly listId = `search-select-${SearchSelectComponent.nextId++}`;

  constructor() {
    effect(() => {
      const value = this.value();
      if (!this.open()) this.query.set(value);
    });
  }

  readonly filteredOptions = computed(() => {
    const needle = this.query().trim().toLocaleLowerCase();
    const options = this.options();
    if (!needle || needle === this.value().toLocaleLowerCase()) return options;
    return options.filter((option) => option.toLocaleLowerCase().includes(needle));
  });

  @HostListener('document:mousedown', ['$event'])
  closeWhenClickingOutside(event: MouseEvent): void {
    if (!this.host.nativeElement.contains(event.target as Node)) this.closeList();
  }

  openList(): void {
    if (!this.open()) this.query.set(this.value());
    this.open.set(true);
  }

  toggleList(): void {
    this.open() ? this.closeList() : this.openList();
  }

  closeList(): void {
    this.open.set(false);
    this.query.set(this.value());
  }

  updateQuery(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
    this.open.set(true);
  }

  selectFirst(event: Event): void {
    if (!this.open()) return;
    const first = this.filteredOptions()[0];
    if (!first) return;
    event.preventDefault();
    this.choose(first);
  }

  choose(option: string): void {
    this.query.set(option);
    this.open.set(false);
    this.valueChange.emit(option);
  }
}
