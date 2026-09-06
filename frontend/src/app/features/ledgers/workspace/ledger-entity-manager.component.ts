import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Observable, Subscription, finalize, forkJoin, map } from 'rxjs';
import { ApiErrorService } from '../../../core/api/api-error';
import { I18nService } from '../../../core/i18n/i18n.service';
import { LedgerAccount, LedgerCurrency } from '../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../core/ledgers/ledger-entities.service';
import { LedgerContextService } from '../../../core/ledgers/ledger-context.service';
import { EntityBadgeComponent } from '../../../shared/ledger/entity-badge.component';
import { FormMessageComponent } from '../../../shared/ui/form-message.component';
import { IconComponent } from '../../../shared/ui/icon.component';
import { EntityEditorComponent } from './entity-editor.component';
import { LedgerEntityPanelService } from './ledger-entity-panel.service';

type Kind = 'account' | 'currency';
type Entity = LedgerAccount | LedgerCurrency;

@Component({
  selector: 'app-ledger-entity-manager',
  imports: [IconComponent, EntityBadgeComponent, FormMessageComponent, EntityEditorComponent],
  templateUrl: './ledger-entity-manager.component.html',
  styleUrl: './ledger-entity-manager.component.scss',
  host: { '[class.currency-section]': "kind() === 'currency'" },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerEntityManagerComponent {
  private readonly entities = inject(LedgerEntitiesService);
  readonly context = inject(LedgerContextService);
  private readonly errors = inject(ApiErrorService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly entityPanel = inject(LedgerEntityPanelService);
  private request?: Subscription;
  readonly i18n = inject(I18nService);
  readonly kind = input.required<Kind>();
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly items = signal<Entity[]>([]);
  readonly currencies = signal<LedgerCurrency[]>([]);
  readonly search = signal('');
  readonly selectedUuid = signal<string | null>(null);
  readonly editorOpen = signal(false);
  readonly deleting = signal<Entity | null>(null);
  readonly deletingBusy = signal(false);
  readonly deleteError = signal<string | null>(null);
  readonly filtered = computed(() => {
    const query = this.search().trim().toLocaleLowerCase();
    return this.items().filter(item => item.name.toLocaleLowerCase().includes(query));
  });
  readonly visible = computed(() => this.filtered());
  readonly title = computed(() => this.i18n.t(this.kind() === 'account' ? 'ledgerShell.accounts' : 'ledgerShell.currencies'));

  constructor() {
    effect(() => {
      const uuid = this.context.ledgerUuid();
      this.kind();
      untracked(() => {
        this.search.set('');
        this.selectedUuid.set(null);
        this.editorOpen.set(false);
        this.deleting.set(null);
        this.entityPanel.close(this);
        if (uuid) this.load();
      });
    });
    this.destroyRef.onDestroy(() => {
      this.request?.unsubscribe();
      this.entityPanel.close(this);
    });
  }

  filter(event: Event): void {
    this.search.set((event.target as HTMLInputElement).value);
    this.selectedUuid.set(null);
    this.entityPanel.close(this);
  }

  select(item: Entity): void {
    this.selectedUuid.set(item.uuid);
    this.showPanel(item);
  }

  load(): void {
    const uuid = this.context.ledgerUuid();
    if (!uuid) return;
    this.request?.unsubscribe();
    this.loading.set(true);
    this.error.set(null);
    const request: Observable<Entity[]> = this.kind() === 'account'
      ? forkJoin({ accounts: this.entities.listAccounts(uuid), currencies: this.entities.listCurrencies(uuid) }).pipe(
          map(({ accounts, currencies }) => { this.currencies.set(currencies); return accounts; }),
        )
      : this.entities.listCurrencies(uuid);
    this.request = request.pipe(finalize(() => this.loading.set(false))).subscribe({
      next: items => {
        this.items.set(items);
        const selected = items.find(item => item.uuid === this.selectedUuid()) ?? null;
        if (selected) this.showPanel(selected);
        else this.entityPanel.close(this);
      },
      error: error => {
        this.entityPanel.close(this);
        this.error.set(this.errors.message(error, this.kind() === 'account' ? 'errors.accountsLoadFailed' : 'errors.currenciesLoadFailed'));
      },
    });
  }

  openCreate(): void {
    this.editorOpen.set(true);
  }

  saved(item: Entity): void {
    this.editorOpen.set(false);
    this.selectedUuid.set(item.uuid);
    this.load();
  }

  confirmDelete(item: Entity): void {
    this.deleteError.set(null);
    this.deleting.set(item);
  }

  closeDelete(): void {
    if (!this.deletingBusy()) this.deleting.set(null);
  }

  remove(): void {
    const item = this.deleting(), uuid = this.context.ledgerUuid();
    if (!item || !uuid || this.deletingBusy()) return;
    this.deletingBusy.set(true);
    this.deleteError.set(null);
    const request = this.kind() === 'account'
      ? this.entities.deleteAccount(uuid, item.uuid)
      : this.entities.deleteCurrency(uuid, item.uuid);
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.deletingBusy.set(false))).subscribe({
      next: () => {
        this.deleting.set(null);
        this.selectedUuid.set(null);
        this.entityPanel.close(this);
        this.load();
      },
      error: error => this.deleteError.set(this.errors.message(error, this.kind() === 'account' ? 'errors.accountDeleteFailed' : 'errors.currencyDeleteFailed')),
    });
  }

  private showPanel(item: Entity): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (!ledgerUuid) return;
    const current = this.entityPanel.state();
    if (current?.owner === this) {
      this.entityPanel.update(this, { entity: item, currencies: this.currencies() });
      return;
    }
    this.entityPanel.show({
      owner: this,
      kind: this.kind(),
      ledgerUuid,
      entity: item,
      currencies: this.currencies(),
      onClose: () => this.selectedUuid.set(null),
      onSaved: saved => this.saved(saved),
      onDeleteRequested: selected => this.confirmDelete(selected),
    });
  }
}
