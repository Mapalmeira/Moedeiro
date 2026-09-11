import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, HostListener, Injector, afterNextRender, computed, inject, input, output, signal } from '@angular/core';
import { DismissiblePopoverDirective } from '../ui/dismissible-popover.directive';
import { normalizeSearchText } from '../search-normalization';
import { EntityBadgeComponent } from './entity-badge.component';
import { DropdownSearchAutofocusDirective } from '../ui/dropdown-search-autofocus.directive';
import { IconComponent, IconName } from '../ui/icon.component';
import { isListboxNavigationKey, nextListboxIndex } from '../ui/listbox-navigation';

type EntitySearchOptionTone = 'green' | 'yellow' | 'blue' | 'neutral';

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
  imports: [DismissiblePopoverDirective, DropdownSearchAutofocusDirective, EntityBadgeComponent, IconComponent],
  template: `
    <div class="entity-search-select" [class.entity-search-select--up]="opensUp()" [appDismissiblePopover]="open()" (dismiss)="closeList()">
      <button type="button" class="entity-search-select__trigger ui-select-trigger ui-trigger-with-icon" (click)="toggleList()"
        [disabled]="disabled()" [attr.aria-label]="ariaLabel()" aria-haspopup="listbox" [attr.aria-expanded]="open()" [attr.aria-controls]="listId"
        [attr.aria-activedescendant]="!searchable() && open() ? activeOptionId() : null" (keydown)="handleTriggerKeydown($event)">
        @if (selectedOption(); as option) {
          @if (option.icon && option.color) {
            <app-entity-badge [icon]="option.icon" [color]="option.color" />
          } @else if (option.uiIcon) {
            <span class="entity-search-select__option-icon ui-icon-badge ui-projected-icon"
              [class.ui-icon-badge--green]="option.tone === 'green'"
              [class.ui-icon-badge--yellow]="option.tone === 'yellow'"
              [class.ui-icon-badge--blue]="option.tone === 'blue'"
              [class.ui-icon-badge--neutral]="!option.tone || option.tone === 'neutral'">
              <app-icon [name]="option.uiIcon" size="badge" />
            </span>
          }
          <span class="entity-search-select__copy">
            <strong>{{ option.label }}</strong>
            @if (option.detail) { <small>{{ option.detail }}</small> }
          </span>
        } @else {
          <span class="entity-search-select__empty-value">{{ emptyValueText() }}</span>
        }
        <app-icon class="ui-select-chevron" name="LucideChevronDown" size="compact" />
      </button>

      @if (open()) {
        <div class="entity-search-select__panel ui-dropdown-panel" [class.entity-search-select__panel--searchable]="searchable()"
          [style.--entity-search-available-height]="availableHeight() + 'px'">
          @if (searchable()) {
            <label class="ui-dropdown-search">
              <app-icon name="LucideSearch" size="control" />
              <input type="search" role="combobox" autocomplete="off" [attr.aria-label]="searchPlaceholder() || ariaLabel()"
                aria-autocomplete="list" [attr.aria-expanded]="open()" [attr.aria-controls]="listId" [attr.aria-activedescendant]="activeOptionId()"
                [placeholder]="searchPlaceholder()" [value]="query()" (input)="updateQuery($event)"
                (keydown)="handleSearchKeydown($event)" appDropdownSearchAutofocus />
            </label>
          }

          <div class="entity-search-select__list" role="listbox" [id]="listId">
            @for (option of filteredOptions(); track option.value; let optionIndex = $index) {
              <button type="button" class="ui-menu-option-with-icon" role="option" [id]="optionId(optionIndex)" tabindex="-1"
                [attr.aria-selected]="value() === option.value" (click)="choose(option.value)">
                @if (option.icon && option.color) {
                  <app-entity-badge [icon]="option.icon" [color]="option.color" />
                } @else if (option.uiIcon) {
                  <span class="entity-search-select__option-icon ui-icon-badge ui-projected-icon"
                    [class.ui-icon-badge--green]="option.tone === 'green'"
                    [class.ui-icon-badge--yellow]="option.tone === 'yellow'"
                    [class.ui-icon-badge--blue]="option.tone === 'blue'"
                    [class.ui-icon-badge--neutral]="!option.tone || option.tone === 'neutral'">
                    <app-icon [name]="option.uiIcon" size="badge" />
                  </span>
                }
                <span class="entity-search-select__copy">
                  <strong>{{ option.label }}</strong>
                  @if (option.detail) { <small>{{ option.detail }}</small> }
                </span>
                @if (value() === option.value) { <app-icon name="LucideCheck" size="compact" /> }
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
      text-align: left;
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
      max-height: min(var(--search-dropdown-max-height), var(--entity-search-available-height, 100dvh));
      grid-template-rows: minmax(0, 1fr);
      overflow: hidden;
    }
    .entity-search-select__panel--searchable { grid-template-rows: auto minmax(0, 1fr); }
    .entity-search-select--up .entity-search-select__panel { top: auto; bottom: calc(100% + var(--space-2)); }
    .entity-search-select__list { min-height: 0; overflow-y: auto; overscroll-behavior: contain; display: grid; align-content: start; gap: var(--space-1); }
    .entity-search-select__list button {
      width: 100%;
      min-height: var(--menu-item-height);
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
    .entity-search-select__list button[aria-selected='true']:hover { background: var(--ui-accent-soft, var(--green-soft)); }
    .entity-search-select__empty { padding: var(--space-3); color: var(--text-muted); font-size: var(--control-font-size); text-align: center; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntitySearchSelectComponent {
  private static nextId = 0;
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly destroyRef = inject(DestroyRef);
  private readonly injector = inject(Injector);
  private geometryObserver?: ResizeObserver;

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
  readonly activeIndex = signal(-1);
  readonly opensUp = signal(false);
  readonly availableHeight = signal(0);
  readonly listId = `entity-search-select-${EntitySearchSelectComponent.nextId++}`;
  private readonly optionIndex = computed(() => new Map(this.options().map(option => [option.value, option] as const)));
  private readonly searchableOptions = computed(() => this.options().map(option => ({
    option,
    searchText: normalizeSearchText(`${option.label} ${option.detail ?? ''}`),
  })));
  readonly selectedOption = computed(() => this.optionIndex().get(this.value()) ?? null);
  readonly filteredOptions = computed(() => {
    const needle = normalizeSearchText(this.query().trim());
    if (!needle || !this.searchable()) return this.options();
    return this.searchableOptions().filter(entry => entry.searchText.includes(needle)).map(entry => entry.option);
  });
  readonly activeOptionId = computed(() => this.activeIndex() >= 0 ? this.optionId(this.activeIndex()) : null);

  constructor() {
    const visualViewport = typeof window === 'undefined' ? null : window.visualViewport;
    const reposition = (event: Event) => {
      // Scrolling the options does not change the trigger's position.
      if (event.target instanceof Node && this.host.nativeElement.contains(event.target)) return;
      if (this.open()) this.resolvePanelGeometry();
    };
    visualViewport?.addEventListener('resize', reposition);
    visualViewport?.addEventListener('scroll', reposition);
    this.host.nativeElement.ownerDocument.addEventListener('scroll', reposition, true);
    this.destroyRef.onDestroy(() => {
      visualViewport?.removeEventListener('resize', reposition);
      visualViewport?.removeEventListener('scroll', reposition);
      this.host.nativeElement.ownerDocument.removeEventListener('scroll', reposition, true);
      this.geometryObserver?.disconnect();
    });
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
    this.syncActiveIndex();
    afterNextRender(() => {
      if (!this.open()) return;
      this.resolvePanelGeometry();
      if (typeof ResizeObserver === 'undefined') return;
      this.geometryObserver?.disconnect();
      this.geometryObserver = new ResizeObserver(() => this.resolvePanelGeometry());
      // Sidebar changes resize ancestors without a window resize event.
      for (let element: HTMLElement | null = this.host.nativeElement; element; element = element.parentElement) {
        this.geometryObserver.observe(element);
      }
    }, { injector: this.injector });
  }

  closeList(): void {
    this.geometryObserver?.disconnect();
    this.open.set(false);
    this.query.set('');
    this.activeIndex.set(-1);
  }

  updateQuery(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
    this.syncActiveIndex();
  }

  handleTriggerKeydown(event: KeyboardEvent): void {
    if (isListboxNavigationKey(event.key)) {
      event.preventDefault();
      if (!this.open()) this.openList();
      else this.moveActive(event.key);
      return;
    }
    if (!this.searchable() && this.open() && (event.key === 'Enter' || event.key === ' ')) {
      const option = this.filteredOptions()[this.activeIndex()];
      if (!option) return;
      event.preventDefault();
      this.choose(option.value);
    }
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
      const option = this.filteredOptions()[this.activeIndex()];
      if (!option) return;
      event.preventDefault();
      this.choose(option.value);
    }
  }

  optionId(index: number): string {
    return `${this.listId}-option-${index}`;
  }

  choose(value: string): void {
    this.closeList();
    this.valueChange.emit(value);
  }

  private syncActiveIndex(): void {
    const options = this.filteredOptions();
    const selectedIndex = options.findIndex(option => option.value === this.value());
    this.activeIndex.set(selectedIndex >= 0 ? selectedIndex : options.length ? 0 : -1);
    this.scrollActiveOption();
  }

  private moveActive(key: 'ArrowDown' | 'ArrowUp' | 'Home' | 'End'): void {
    this.activeIndex.set(nextListboxIndex(this.activeIndex(), this.filteredOptions().length, key));
    this.scrollActiveOption();
  }

  private scrollActiveOption(): void {
    const id = this.activeOptionId();
    if (!id) return;
    afterNextRender(() => this.host.nativeElement.ownerDocument.getElementById(id)?.scrollIntoView?.({ block: 'nearest' }), { injector: this.injector });
  }

  private resolvePanelGeometry(): void {
    if (typeof window === 'undefined') return;
    const trigger = this.host.nativeElement.querySelector<HTMLElement>('.entity-search-select__trigger');
    if (!trigger) return;

    const triggerBounds = trigger.getBoundingClientRect();
    const visualViewport = window.visualViewport;
    const viewportTop = visualViewport?.offsetTop ?? 0;
    const viewportBottom = viewportTop + (visualViewport?.height ?? window.innerHeight);
    let topBoundary = viewportTop;
    let bottomBoundary = viewportBottom;
    for (let ancestor = this.host.nativeElement.parentElement; ancestor; ancestor = ancestor.parentElement) {
      if (!/^(auto|scroll|hidden|clip)$/.test(getComputedStyle(ancestor).overflowY)) continue;
      const bounds = ancestor.getBoundingClientRect();
      const contentTop = bounds.top + ancestor.clientTop;
      topBoundary = Math.max(topBoundary, contentTop);
      bottomBoundary = Math.min(bottomBoundary, contentTop + ancestor.clientHeight);
    }
    const spaceAbove = Math.max(0, triggerBounds.top - topBoundary);
    const spaceBelow = Math.max(0, bottomBoundary - triggerBounds.bottom);
    const styles = getComputedStyle(this.host.nativeElement);
    const panelGap = Number.parseFloat(styles.getPropertyValue('--space-2')) || 0;
    const panelShadow = Number.parseFloat(styles.getPropertyValue('--button-shadow-offset')) || 0;
    const maxPanelHeight = Number.parseFloat(styles.getPropertyValue('--search-dropdown-max-height')) || Number.POSITIVE_INFINITY;
    const panel = this.host.nativeElement.querySelector<HTMLElement>('.entity-search-select__panel');
    const list = panel?.querySelector<HTMLElement>('.entity-search-select__list');
    const contentHeight = panel && list ? panel.offsetHeight - list.clientHeight + list.scrollHeight : maxPanelHeight;
    const desiredHeight = Math.min(contentHeight, maxPanelHeight);
    const usableAbove = Math.max(0, spaceAbove - panelGap);
    const usableBelow = Math.max(0, spaceBelow - panelGap - panelShadow);
    const direction = this.openDirection();
    const autoOpensUp = desiredHeight > usableBelow && (desiredHeight <= usableAbove || usableAbove > usableBelow);
    const opensUp = direction === 'up' || (direction === 'auto' && autoOpensUp);

    this.opensUp.set(opensUp);
    this.availableHeight.set(opensUp ? usableAbove : usableBelow);
  }
}
