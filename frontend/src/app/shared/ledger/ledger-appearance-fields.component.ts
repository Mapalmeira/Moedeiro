import { ChangeDetectionStrategy, Component, ElementRef, Injector, afterNextRender, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { DismissiblePopoverDirective } from '../ui/dismissible-popover.directive';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { I18nService } from '../../core/i18n/i18n.service';
import { normalizeSearchText } from '../search-normalization';
import { DropdownSearchAutofocusDirective } from '../ui/dropdown-search-autofocus.directive';
import { InfiniteScrollTriggerDirective } from '../ui/infinite-scroll-trigger.directive';
import { IconComponent } from '../ui/icon.component';
import { isListboxNavigationKey, nextListboxIndex } from '../ui/listbox-navigation';
import { LedgerColorFieldComponent } from './ledger-color-field.component';
import { DEFAULT_LEDGER_APPEARANCE } from './ledger-appearance';
import { LedgerIconComponent } from './ledger-icon.component';
import { decodeLucideLedgerIcon, decodeUnicodeLedgerIcon, encodeLucideLedgerIcon, encodeUnicodeLedgerIcon, isEncodedLucideLedgerIcon } from './ledger-icon-value';
import { LUCIDE_ICON_CATALOG, resolveLucideIcon, resolveLucideIconLabel } from './lucide-icon-catalog';

const ICON_BATCH_SIZE = 48;

type IconMode = 'lucide' | 'unicode';

@Component({
  selector: 'app-ledger-appearance-fields',
  standalone: true,
  imports: [DismissiblePopoverDirective, ReactiveFormsModule, IconComponent, LedgerIconComponent, DropdownSearchAutofocusDirective, InfiniteScrollTriggerDirective, LedgerColorFieldComponent],
  template: `
    <app-ledger-color-field [colorControl]="colorControl()" />
    <section class="appearance-field icon-field">
      <span class="field-label">{{ i18n.t('ledgers.editor.icon') }}</span>
      <div class="mode-switch" role="group" [attr.aria-label]="i18n.t('ledgers.editor.icon')">
        <button type="button" class="ui-choice ui-choice--projected-centered mode-switch__button" [class.ui-choice--selected]="iconMode() === 'lucide'" (click)="setMode('lucide')"><span class="ui-choice__content">Lucide</span></button>
        <button type="button" class="ui-choice ui-choice--projected-centered mode-switch__button" [class.ui-choice--selected]="iconMode() === 'unicode'" (click)="setMode('unicode')"><span class="ui-choice__content">Unicode</span></button>
      </div>
      <div class="icon-control-slot">
        @if (iconMode() === 'lucide') {
          <div class="lucide-picker" [appDismissiblePopover]="pickerOpen()" (dismiss)="dismissPicker()">
            <button type="button" class="lucide-picker__trigger ui-select-trigger" (click)="togglePicker()" [attr.aria-label]="i18n.t('ledgers.editor.icon')" aria-haspopup="listbox" [attr.aria-expanded]="pickerOpen()" [attr.aria-controls]="listId">
              <span class="selected-icon"><app-ledger-icon [icon]="iconControl().value" [size]="22" /></span><span>{{ selectedLabel() }}</span><app-icon class="ui-select-chevron" name="chevron-down" size="chevron" />
            </button>
            @if (pickerOpen()) {
              <div class="picker-panel ui-dropdown-panel" (keydown.escape)="closePicker($event)">
                <label class="icon-search ui-dropdown-search"><app-icon name="search" size="action" /><input type="search" role="combobox" aria-autocomplete="list" [attr.aria-expanded]="pickerOpen()" [attr.aria-controls]="listId" [attr.aria-activedescendant]="activeOptionId()" [attr.aria-label]="i18n.t('ledgers.editor.icon')" [value]="search()" (input)="updateSearch($event)" (keydown)="handleSearchKeydown($event)" appDropdownSearchAutofocus /></label>
                <div class="icon-grid" role="listbox" [id]="listId" [attr.aria-label]="i18n.t('ledgers.editor.icon')">
                  @for (entry of visibleIcons(); track entry.id; let iconIndex = $index) { <button type="button" class="ui-choice icon-choice" role="option" [id]="optionId(iconIndex)" tabindex="-1" [attr.aria-selected]="currentLucideId() === entry.id" (click)="selectLucide(entry.id)" [title]="entry.label"><app-ledger-icon [icon]="'lucide:' + entry.id" [size]="22" /><span>{{ entry.label }}</span></button> }
                  @if (hasMoreIcons()) {
                    <span class="icon-grid__sentinel" appInfiniteScrollTrigger rootMargin="96px 0px" (triggered)="loadMoreIcons()" aria-hidden="true"></span>
                  }
                </div>
              </div>
            }
          </div>
        } @else {
          <label class="field unicode-field"><input type="text" [attr.aria-label]="i18n.t('ledgers.editor.icon')" [value]="unicodeValue()" (input)="setUnicode($event)" autocomplete="off" maxlength="12" /></label>
        }
      </div>
    </section>
  `,
  styles: `
    .ui-choice--selected { background: color-mix(in srgb, var(--ui-accent, var(--green)) 15%, var(--surface)); }
    .ui-dropdown-search:focus-within, .ui-select-trigger[aria-expanded=true] { border-color: var(--ui-accent-strong, var(--green-strong)); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ui-accent, var(--green)) 32%, transparent); }
    .selected-icon { overflow: hidden; }
    :host { display: grid; gap: var(--space-4); }
    .appearance-field { display: grid; gap: var(--field-gap); min-width: 0; }
    .field-label { font-size: var(--control-font-size); font-weight: 780; }
    .mode-switch { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-2); }
    .mode-switch__button { min-height: var(--control-height); font-weight: 760; }
    .icon-control-slot { position: relative; min-height: var(--control-height); margin-top: var(--space-2); }
    .lucide-picker { position: relative; }
    .lucide-picker__trigger { width: 100%; height: var(--control-height); display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; align-items: center; gap: var(--space-2); padding: 0 var(--space-3) 0 var(--space-2); text-align: left; font-weight: 650; }
    .selected-icon { width: 32px; height: 32px; display: grid; place-items: center; border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-icon); background: var(--surface-muted); }
    .picker-panel { position: absolute; z-index: var(--layer-dropdown); inset-inline: 0; bottom: calc(100% + var(--space-2)); }
    .icon-grid { max-height: min(196px, 28dvh); overflow: auto; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-2); padding: var(--space-1); }
    .icon-grid__sentinel { grid-column: 1 / -1; min-height: var(--space-1); }
    .icon-choice { min-width: 0; min-height: var(--list-row-height); display: grid; justify-items: center; align-content: center; gap: var(--space-1); padding: var(--space-2); }
    .icon-choice span { width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .7rem; font-weight: 680; }
    .unicode-field { gap: 0; }
    .unicode-field input { text-align: center; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerAppearanceFieldsComponent {
  private static nextId = 0;
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly injector = inject(Injector);
  readonly i18n = inject(I18nService);
  readonly iconControl = input.required<FormControl<string>>();
  readonly colorControl = input.required<FormControl<string>>();
  readonly iconMode = signal<IconMode>('lucide');
  readonly pickerOpen = signal(false);
  readonly search = signal('');
  readonly activeIndex = signal(-1);
  readonly listId = `ledger-icon-picker-${LedgerAppearanceFieldsComponent.nextId++}`;
  readonly visibleIconCount = signal(ICON_BATCH_SIZE);
  readonly filteredIcons = computed(() => {
    const query = normalizeSearchText(this.search().trim());
    return query ? LUCIDE_ICON_CATALOG.filter(entry => entry.searchText.includes(query)) : LUCIDE_ICON_CATALOG;
  });
  readonly visibleIcons = computed(() => this.filteredIcons().slice(0, this.visibleIconCount()));
  readonly hasMoreIcons = computed(() => this.visibleIcons().length < this.filteredIcons().length);
  readonly currentIcon = signal(DEFAULT_LEDGER_APPEARANCE.icon);
  readonly currentLucideId = computed(() => decodeLucideLedgerIcon(this.currentIcon()));
  readonly activeOptionId = computed(() => this.activeIndex() >= 0 ? this.optionId(this.activeIndex()) : null);
  readonly selectedLabel = computed(() => resolveLucideIconLabel(decodeLucideLedgerIcon(this.currentIcon())));
  readonly unicodeValue = computed(() => decodeUnicodeLedgerIcon(this.currentIcon()));

  constructor() {
    effect((onCleanup) => {
      const icon = this.iconControl();
      const syncIcon = (value: string) => { this.currentIcon.set(value); this.iconMode.set(isEncodedLucideLedgerIcon(value) ? 'lucide' : 'unicode'); };
      untracked(() => syncIcon(icon.value));
      const subscription = icon.valueChanges.subscribe(syncIcon);
      onCleanup(() => subscription.unsubscribe());
    });
  }

  closePicker(event: Event): void { event.preventDefault(); event.stopPropagation(); this.dismissPicker(); }
  dismissPicker(): void { this.pickerOpen.set(false); this.activeIndex.set(-1); }
  togglePicker(): void {
    this.pickerOpen.update(value => !value);
    if (this.pickerOpen()) { this.search.set(''); this.visibleIconCount.set(ICON_BATCH_SIZE); this.syncActiveIndex(); }
    else this.activeIndex.set(-1);
  }
  updateSearch(event: Event): void { this.search.set((event.target as HTMLInputElement).value); this.visibleIconCount.set(ICON_BATCH_SIZE); this.syncActiveIndex(); }
  handleSearchKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') { this.closePicker(event); return; }
    if (isListboxNavigationKey(event.key)) { event.preventDefault(); this.moveActive(event.key); return; }
    if (event.key === 'Enter') {
      const entry = this.visibleIcons()[this.activeIndex()];
      if (!entry) return;
      event.preventDefault();
      this.selectLucide(entry.id);
    }
  }
  optionId(index: number): string { return `${this.listId}-option-${index}`; }
  loadMoreIcons(): void { if (this.hasMoreIcons()) this.visibleIconCount.update(count => Math.min(count + ICON_BATCH_SIZE, this.filteredIcons().length)); }
  setMode(mode: IconMode): void { this.dismissPicker(); this.iconMode.set(mode); if (mode === 'lucide' && !resolveLucideIcon(decodeLucideLedgerIcon(this.iconControl().value))) this.iconControl().setValue(DEFAULT_LEDGER_APPEARANCE.icon); if (mode === 'unicode' && isEncodedLucideLedgerIcon(this.iconControl().value)) this.iconControl().setValue(encodeUnicodeLedgerIcon('💰')); this.iconControl().markAsDirty(); }
  selectLucide(icon: string): void { this.iconControl().setValue(encodeLucideLedgerIcon(icon)); this.iconControl().markAsDirty(); this.dismissPicker(); }
  private syncActiveIndex(): void {
    const icons = this.visibleIcons();
    const selected = icons.findIndex(entry => entry.id === this.currentLucideId());
    this.activeIndex.set(selected >= 0 ? selected : icons.length ? 0 : -1);
    this.scrollActiveOption();
  }
  private moveActive(key: 'ArrowDown' | 'ArrowUp' | 'Home' | 'End'): void {
    this.activeIndex.set(nextListboxIndex(this.activeIndex(), this.visibleIcons().length, key));
    this.scrollActiveOption();
  }
  private scrollActiveOption(): void {
    const id = this.activeOptionId();
    if (!id) return;
    afterNextRender(() => this.host.nativeElement.ownerDocument.getElementById(id)?.scrollIntoView?.({ block: 'nearest' }), { injector: this.injector });
  }
  setUnicode(event: Event): void { const input = event.target as HTMLInputElement; const value = Array.from(input.value).slice(0, 3).join(''); input.value = value; this.iconControl().setValue(encodeUnicodeLedgerIcon(value)); this.iconControl().markAsDirty(); }
}
