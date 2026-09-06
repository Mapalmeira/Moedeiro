import { ChangeDetectionStrategy, Component, HostListener, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../../core/api/api-error';
import { I18nService } from '../../../core/i18n/i18n.service';
import { Ledger } from '../../../core/ledgers/ledger.models';
import { LedgerService } from '../../../core/ledgers/ledger.service';
import { bestContrastingForeground } from '../../../shared/ledger/ledger-appearance';
import { LedgerIconComponent } from '../../../shared/ledger/ledger-icon.component';
import { FormMessageComponent } from '../../../shared/ui/form-message.component';
import { IconComponent } from '../../../shared/ui/icon.component';
import { LedgerDeleteDialogComponent } from '../ledger-delete-dialog.component';
import { LedgerEditorDialogComponent } from '../ledger-editor-dialog.component';

@Component({
  selector: 'app-ledger-selector',
  standalone: true,
  imports: [FormMessageComponent, IconComponent, LedgerIconComponent, LedgerEditorDialogComponent, LedgerDeleteDialogComponent],
  template: `
    <section class="ledger-card ui-projected-surface ui-projection--hard" aria-labelledby="ledgers-title">
      <header class="ledger-card__header">
        <div class="ledger-card__title ui-heading-with-icon">
          <span class="ledger-card__title-icon ui-icon-badge ui-icon-badge--title ui-projected-icon" aria-hidden="true"><app-icon name="database" [size]="25" /></span>
          <h1 id="ledgers-title">{{ i18n.t('ledgers.title') }}</h1>
        </div>
        <button class="ui-button ui-button--green create-button" type="button" (click)="openCreate()">
          <app-icon name="plus" [size]="18" />
          <span>{{ i18n.t('ledgers.create') }}</span>
        </button>
      </header>

      <div class="ledger-card__body">
        <label class="search-box ui-dropdown-search">
          <app-icon name="search" [size]="19" />
          <input type="search" [value]="search()" (input)="setSearchFromEvent($event)" [placeholder]="i18n.t('ledgers.search')" />
        </label>

        @if (loadError()) {
          <app-form-message [text]="loadError()!" />
        } @else if (loading()) {
          <div class="state-row"><span class="ui-spinner" aria-hidden="true"></span><span>{{ i18n.t('ledgers.loading') }}</span></div>
        } @else if (filteredLedgers().length === 0) {
          <div class="empty-state">
            <span class="empty-state__icon"><app-icon name="book" [size]="25" /></span>
            <strong>{{ search().trim() ? i18n.t('ledgers.noSearchResults') : i18n.t('ledgers.empty') }}</strong>
          </div>
        } @else {
          <div class="ledger-list" role="listbox" [attr.aria-label]="i18n.t('ledgers.title')">
            @for (ledger of filteredLedgers(); track ledger.uuid) {
              <div class="ledger-row" role="option" tabindex="0" [attr.aria-selected]="selectedUuid() === ledger.uuid"
                [class.ledger-row--selected]="selectedUuid() === ledger.uuid"
                (click)="selectLedger(ledger.uuid)" (keydown.enter)="selectLedger(ledger.uuid)" (keydown.space)="selectLedgerFromSpace($event, ledger.uuid)">
                <span class="ledger-row__token ui-icon-badge ui-icon-badge--title ui-projected-icon" [style.background]="ledger.color_code" [style.color]="foreground(ledger.color_code)">
                  <app-ledger-icon [icon]="ledger.icon" [size]="25" />
                </span>
                <strong class="ledger-row__name">{{ ledger.name }}</strong>

                <div class="ledger-row__actions">
                  <button class="more-button" type="button" (click)="toggleMenu($event, ledger.uuid)"
                    [attr.aria-label]="i18n.t('ledgers.actions')" [attr.aria-expanded]="menuLedgerUuid() === ledger.uuid">
                    <app-icon name="ellipsis" [size]="20" />
                  </button>
                  @if (menuLedgerUuid() === ledger.uuid) {
                    <div class="row-menu ui-dropdown-menu ui-projected-surface ui-projection--surface" role="menu" (click)="$event.stopPropagation()">
                      <button type="button" role="menuitem" (click)="openEdit(ledger)">
                        <span class="row-menu__icon row-menu__icon--blue ui-icon-badge ui-projected-icon"><app-icon name="pencil" [size]="16" /></span>
                        <span>{{ i18n.t('ledgers.edit') }}</span>
                      </button>
                      <button class="row-menu__delete" type="button" role="menuitem" (click)="openDelete(ledger)">
                        <span class="row-menu__icon row-menu__icon--danger ui-icon-badge ui-projected-icon"><app-icon name="trash" [size]="16" /></span>
                        <span>{{ i18n.t('ledgers.delete') }}</span>
                      </button>
                    </div>
                  }
                </div>
              </div>
            }
          </div>
        }
      </div>

      <footer class="ledger-card__footer">
        <button class="ui-button ui-button--green enter-button" type="button" [disabled]="!selectedLedger() || entering()" (click)="enterSelected()">
          <span>{{ i18n.t('ledgers.enter') }}</span>
          <app-icon name="arrow-right" [size]="19" />
        </button>
      </footer>
    </section>

    <app-ledger-editor-dialog [open]="editorOpen()" [ledger]="editingLedger()" (close)="closeEditor()" (saved)="onSaved($event)" />
    <app-ledger-delete-dialog [open]="deleteOpen()" [ledger]="deletingLedger()" (close)="closeDelete()" (deleted)="onDeleted($event)" />
  `,
  styles: `
    :host { display: grid; justify-items: center; width: 100%; }
    .ledger-card {
      --token-accent: var(--green); --token-accent-strong: var(--green-strong); --focus-accent: var(--green);
      --ledger-list-min-height: 160px;
      width: min(760px, calc(100% - var(--hard-shadow-offset))); margin-inline-end: var(--hard-shadow-offset); margin-block-end: var(--hard-shadow-offset); border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-card);
      background: var(--surface); color: var(--text); overflow: visible;
    }
    .ledger-card__header { display: flex; align-items: center; justify-content: space-between; gap: var(--section-gap); padding: var(--space-5); border-bottom: var(--border-width) solid var(--line); }
    .ledger-card__title-icon { background: var(--green); color: var(--on-green); }
    h1 { margin: 0; font-size: clamp(1.25rem, 2vw, 1.48rem); line-height: var(--heading-line-height); letter-spacing: -.015em; }
    .create-button { flex: 0 0 auto; padding-inline: var(--space-4); }
    .ledger-card__body { display: grid; gap: var(--form-gap); padding: var(--space-5); }
    .search-box { height: var(--control-height); }
    .ledger-list { display: grid; min-height: var(--ledger-list-min-height); align-content: start; gap: var(--space-2); min-width: 0; }
    .ledger-row { position: relative; min-height: var(--list-row-height); display: grid; grid-template-columns: calc(var(--title-icon-size) + var(--icon-shadow-offset)) minmax(0, 1fr) auto; align-items: center; gap: var(--title-icon-gap); padding: var(--space-2) var(--space-3); border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-sm); background: var(--surface); box-shadow: var(--selection-shadow-transparent); outline: none; transition: border-color var(--motion-selection) ease, background var(--motion-selection) ease, box-shadow var(--motion-selection) ease; cursor: pointer; }
    .ledger-row:not(.ledger-row--selected):hover { border-color: var(--line-strong); background: var(--surface-muted); }
    .ledger-row:focus-visible { border-color: var(--green-strong); box-shadow: 0 0 0 3px color-mix(in srgb, var(--green) 30%, transparent); }
    .ledger-row.ledger-row--selected { border-color: var(--line-strong); background: var(--green-soft); box-shadow: var(--selection-shadow); }
    .ledger-row__name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .98rem; }
    .ledger-row__actions { position: relative; }
    .more-button { display: grid; place-items: center; width: var(--icon-button-size); height: var(--icon-button-size); padding: 0; border: var(--border-width) solid transparent; border-radius: var(--radius-sm); background: transparent; color: var(--text); }
    .more-button:hover, .more-button[aria-expanded='true'] { border-color: var(--line); background: var(--surface); }
    .row-menu { position: absolute; z-index: var(--layer-dropdown); top: calc(100% + var(--space-2)); right: 0; width: 172px; }
    .row-menu button { width: 100%; min-height: var(--menu-item-height); display: grid; grid-template-columns: var(--control-icon-footprint) minmax(0, 1fr); align-items: center; gap: var(--space-2); padding: var(--space-1) var(--space-2); border: 0; background: transparent; color: var(--text); text-align: left; font-size: var(--control-font-size); font-weight: var(--control-font-weight); }
    .row-menu button:hover { background: var(--surface-muted); }
    .row-menu button + button { margin-top: var(--space-1); }
    .row-menu__icon--blue { background: var(--blue); color: var(--on-blue); }
    .row-menu__icon--danger { background: var(--danger-token); color: var(--on-danger-token); }
    .state-row, .empty-state { min-height: var(--ledger-list-min-height); display: grid; place-items: center; align-content: center; gap: var(--space-3); color: var(--text-muted); text-align: center; }
    .state-row { grid-template-columns: auto auto; justify-content: center; }
    .empty-state__icon { width: var(--touch-target-size); height: var(--touch-target-size); display: grid; place-items: center; border: var(--border-width) solid var(--line); border-radius: var(--radius-card); background: var(--surface-muted); }
    .ledger-card__footer { display: flex; justify-content: flex-end; padding: var(--space-4) var(--space-5) var(--space-5); border-top: 1px solid var(--line); }
    .enter-button { min-width: var(--action-button-min-width); }
    @media (max-width: 600px) {
      .ledger-card__header { align-items: stretch; flex-direction: column; }
      .create-button { width: 100%; }
      .ledger-card__body { padding: var(--space-4); }
      .ledger-card__footer { padding: var(--space-4); }
      .enter-button { width: 100%; }
      .row-menu { right: -2px; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerSelectorComponent {
  private readonly ledgers = inject(LedgerService);
  private readonly apiErrors = inject(ApiErrorService);
  private readonly router = inject(Router);
  readonly i18n = inject(I18nService);

  readonly loading = signal(false);
  readonly entering = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly search = signal('');
  readonly selectedUuid = signal<string | null>(null);
  readonly menuLedgerUuid = signal<string | null>(null);
  readonly editorOpen = signal(false);
  readonly editingLedger = signal<Ledger | null>(null);
  readonly deleteOpen = signal(false);
  readonly deletingLedger = signal<Ledger | null>(null);

  readonly filteredLedgers = computed(() => {
    const query = this.search().trim().toLocaleLowerCase();
    const ledgers = this.ledgers.ledgers();
    return query ? ledgers.filter((ledger) => ledger.name.toLocaleLowerCase().includes(query)) : ledgers;
  });

  readonly selectedLedger = computed(() => {
    const uuid = this.selectedUuid();
    return uuid ? this.ledgers.ledgers().find((ledger) => ledger.uuid === uuid) ?? null : null;
  });

  constructor() {
    this.load();
  }

  @HostListener('document:click')
  closeRowMenu(): void {
    this.menuLedgerUuid.set(null);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.menuLedgerUuid.set(null);
  }

  load(): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.loadError.set(null);
    this.ledgers.list().pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (ledgers) => {
        const selected = this.selectedUuid();
        if (selected && !ledgers.some((ledger) => ledger.uuid === selected)) this.selectedUuid.set(null);
      },
      error: (error: unknown) => this.loadError.set(this.apiErrors.message(error, 'errors.ledgersLoadFailed')),
    });
  }

  setSearchFromEvent(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.search.set(value);
    this.menuLedgerUuid.set(null);

    const selected = this.selectedLedger();
    if (selected && !selected.name.toLocaleLowerCase().includes(value.trim().toLocaleLowerCase())) {
      this.selectedUuid.set(null);
    }
  }

  selectLedger(uuid: string): void {
    this.selectedUuid.set(uuid);
    this.menuLedgerUuid.set(null);
  }

  selectLedgerFromSpace(event: Event, uuid: string): void {
    event.preventDefault();
    this.selectLedger(uuid);
  }

  toggleMenu(event: Event, uuid: string): void {
    event.stopPropagation();
    this.menuLedgerUuid.update((current) => current === uuid ? null : uuid);
  }

  openCreate(): void {
    this.menuLedgerUuid.set(null);
    this.editingLedger.set(null);
    this.editorOpen.set(true);
  }

  openEdit(ledger: Ledger): void {
    this.menuLedgerUuid.set(null);
    this.editingLedger.set(ledger);
    this.editorOpen.set(true);
  }

  closeEditor(): void {
    this.editorOpen.set(false);
    this.editingLedger.set(null);
  }

  onSaved(ledger: Ledger): void {
    this.selectedUuid.set(ledger.uuid);
  }

  openDelete(ledger: Ledger): void {
    this.menuLedgerUuid.set(null);
    this.deletingLedger.set(ledger);
    this.deleteOpen.set(true);
  }

  closeDelete(): void {
    this.deleteOpen.set(false);
    this.deletingLedger.set(null);
  }

  onDeleted(uuid: string): void {
    if (this.selectedUuid() === uuid) this.selectedUuid.set(null);
  }

  enterSelected(): void {
    const ledger = this.selectedLedger();
    if (!ledger || this.entering()) return;
    this.entering.set(true);
    void this.router.navigate(['/ledgers', ledger.uuid, 'home']).finally(() => this.entering.set(false));
  }

  foreground(color: string): string {
    return bestContrastingForeground(color).foreground;
  }
}
