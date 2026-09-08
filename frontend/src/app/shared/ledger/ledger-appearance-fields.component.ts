import { ChangeDetectionStrategy, Component, HostListener, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { I18nService } from '../../core/i18n/i18n.service';
import { InfiniteScrollTriggerDirective } from '../ui/infinite-scroll-trigger.directive';
import { IconComponent } from '../ui/icon.component';
import { LedgerColorFieldComponent } from './ledger-color-field.component';
import { LedgerIconComponent } from './ledger-icon.component';
import { decodeLucideLedgerIcon, decodeUnicodeLedgerIcon, encodeLucideLedgerIcon, encodeUnicodeLedgerIcon, isEncodedLucideLedgerIcon } from './ledger-icon-value';
import { LUCIDE_ICON_CATALOG, resolveLucideIcon, resolveLucideIconLabel } from './lucide-icon-catalog';

const DEFAULT_ICON = 'lucide:WalletCards';
const ICON_BATCH_SIZE = 48;

type IconMode = 'lucide' | 'unicode';

@Component({
  selector: 'app-ledger-appearance-fields',
  standalone: true,
  imports: [ReactiveFormsModule, IconComponent, LedgerIconComponent, InfiniteScrollTriggerDirective, LedgerColorFieldComponent],
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
          <div class="lucide-picker">
            <button type="button" class="lucide-picker__trigger ui-select-trigger" (click)="togglePicker()" [attr.aria-label]="i18n.t('ledgers.editor.icon')" [attr.aria-expanded]="pickerOpen()">
              <span class="selected-icon"><app-ledger-icon [icon]="iconControl().value" [size]="22" /></span><span>{{ selectedLabel() }}</span><app-icon class="ui-select-chevron" name="chevron-down" [size]="17" />
            </button>
            @if (pickerOpen()) {
              <div class="picker-panel ui-dropdown-panel" (keydown.escape)="closePicker($event)">
                <label class="icon-search ui-dropdown-search"><app-icon name="search" [size]="18" /><input type="search" [attr.aria-label]="i18n.t('ledgers.editor.icon')" [value]="search()" (input)="updateSearch($event)" autofocus /></label>
                <div class="icon-grid" role="group" [attr.aria-label]="i18n.t('ledgers.editor.icon')">
                  @for (entry of visibleIcons(); track entry.id) { <button type="button" class="ui-choice icon-choice" (click)="selectLucide(entry.id)" [title]="entry.label"><app-ledger-icon [icon]="'lucide:' + entry.id" [size]="22" /><span>{{ entry.label }}</span></button> }
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
    .ui-choice--selected { background: color-mix(in srgb, var(--token-accent, var(--green)) 15%, var(--surface)); }
    .ui-dropdown-search:focus-within, .ui-select-trigger[aria-expanded=true] { border-color: var(--token-accent-strong, var(--green-strong)); box-shadow: 0 0 0 3px color-mix(in srgb, var(--token-accent, var(--green)) 32%, transparent); }
    .selected-icon { overflow: hidden; }
    :host { display: grid; gap: var(--space-4); }
    .appearance-field { display: grid; gap: var(--field-gap); min-width: 0; }
    .field-label { font-size: .9rem; font-weight: 780; }
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
  readonly i18n = inject(I18nService);
  readonly iconControl = input.required<FormControl<string>>();
  readonly colorControl = input.required<FormControl<string>>();
  readonly iconMode = signal<IconMode>('lucide');
  readonly pickerOpen = signal(false);
  readonly search = signal('');
  readonly visibleIconCount = signal(ICON_BATCH_SIZE);
  readonly filteredIcons = computed(() => {
    const query = this.search().trim().toLocaleLowerCase();
    return query ? LUCIDE_ICON_CATALOG.filter(entry => entry.searchText.includes(query)) : LUCIDE_ICON_CATALOG;
  });
  readonly visibleIcons = computed(() => this.filteredIcons().slice(0, this.visibleIconCount()));
  readonly hasMoreIcons = computed(() => this.visibleIcons().length < this.filteredIcons().length);
  readonly currentIcon = signal(DEFAULT_ICON);
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

  @HostListener('document:mousedown', ['$event'])
  outside(event: MouseEvent): void { if (this.pickerOpen() && !(event.target as Element | null)?.closest('.lucide-picker')) this.pickerOpen.set(false); }
  closePicker(event: Event): void { event.preventDefault(); event.stopPropagation(); this.pickerOpen.set(false); }
  togglePicker(): void { this.pickerOpen.update(value => !value); if (this.pickerOpen()) { this.search.set(''); this.visibleIconCount.set(ICON_BATCH_SIZE); } }
  updateSearch(event: Event): void { this.search.set((event.target as HTMLInputElement).value); this.visibleIconCount.set(ICON_BATCH_SIZE); }
  loadMoreIcons(): void { if (this.hasMoreIcons()) this.visibleIconCount.update(count => Math.min(count + ICON_BATCH_SIZE, this.filteredIcons().length)); }
  setMode(mode: IconMode): void { this.pickerOpen.set(false); this.iconMode.set(mode); if (mode === 'lucide' && !resolveLucideIcon(decodeLucideLedgerIcon(this.iconControl().value))) this.iconControl().setValue(DEFAULT_ICON); if (mode === 'unicode' && isEncodedLucideLedgerIcon(this.iconControl().value)) this.iconControl().setValue(encodeUnicodeLedgerIcon('💰')); this.iconControl().markAsDirty(); }
  selectLucide(icon: string): void { this.iconControl().setValue(encodeLucideLedgerIcon(icon)); this.iconControl().markAsDirty(); this.pickerOpen.set(false); }
  setUnicode(event: Event): void { const input = event.target as HTMLInputElement; const value = Array.from(input.value).slice(0, 3).join(''); input.value = value; this.iconControl().setValue(encodeUnicodeLedgerIcon(value)); this.iconControl().markAsDirty(); }
}
