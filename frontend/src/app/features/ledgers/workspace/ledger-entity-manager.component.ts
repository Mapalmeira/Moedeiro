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
  private request?: Subscription;

  readonly i18n = inject(I18nService);
  readonly kind = input.required<Kind>();
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly items = signal<Entity[]>([]);
  readonly currencies = signal<LedgerCurrency[]>([]);
  readonly search = signal('');
  readonly editorOpen = signal(false);
  readonly editing = signal<Entity | null>(null);
  readonly deleting = signal<Entity | null>(null);
  readonly deletingBusy = signal(false);
  readonly deleteError = signal<string | null>(null);
  readonly filtered = computed(() => {
    const query = this.search().trim().toLocaleLowerCase();
    return this.items().filter(item => item.name.toLocaleLowerCase().includes(query));
  });
  readonly title = computed(() => this.i18n.t(this.kind() === 'account' ? 'ledgerShell.accounts' : 'ledgerShell.currencies'));

  constructor() {
    effect(() => {
      const uuid = this.context.ledgerUuid();
      this.kind();
      untracked(() => {
        this.search.set('');
        this.editorOpen.set(false);
        this.editing.set(null);
        this.deleting.set(null);
        if (uuid) this.load();
      });
    });
    this.destroyRef.onDestroy(() => this.request?.unsubscribe());
  }

  filter(event: Event): void {
    this.search.set((event.target as HTMLInputElement).value);
  }

  edit(item: Entity): void {
    this.editing.set(item);
    this.editorOpen.set(true);
  }

  load(): void {
    const uuid = this.context.ledgerUuid();
    if (!uuid) return;
    this.request?.unsubscribe();
    this.loading.set(true);
    this.error.set(null);
    const request: Observable<Entity[]> = this.kind() === 'account'
      ? forkJoin({ accounts: this.entities.listAccounts(uuid), currencies: this.entities.listCurrencies(uuid) }).pipe(
          map(({ accounts, currencies }) => {
            this.currencies.set(currencies);
            return accounts;
          }),
        )
      : this.entities.listCurrencies(uuid);
    this.request = request.pipe(finalize(() => this.loading.set(false))).subscribe({
      next: items => this.items.set(items),
      error: error => this.error.set(this.errors.message(error, this.kind() === 'account' ? 'errors.accountsLoadFailed' : 'errors.currenciesLoadFailed')),
    });
  }

  openCreate(): void {
    this.editing.set(null);
    this.editorOpen.set(true);
  }

  closeEditor(): void {
    this.editorOpen.set(false);
    this.editing.set(null);
  }

  saved(_: Entity): void {
    this.closeEditor();
    this.load();
  }

  confirmDelete(item: Entity): void {
    this.closeEditor();
    this.deleteError.set(null);
    this.deleting.set(item);
  }

  closeDelete(): void {
    if (!this.deletingBusy()) this.deleting.set(null);
  }

  remove(): void {
    const item = this.deleting();
    const uuid = this.context.ledgerUuid();
    if (!item || !uuid || this.deletingBusy()) return;

    this.deletingBusy.set(true);
    this.deleteError.set(null);
    const request = this.kind() === 'account'
      ? this.entities.deleteAccount(uuid, item.uuid)
      : this.entities.deleteCurrency(uuid, item.uuid);
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.deletingBusy.set(false))).subscribe({
      next: () => {
        this.deleting.set(null);
        this.load();
      },
      error: error => this.deleteError.set(this.errors.message(error, this.kind() === 'account' ? 'errors.accountDeleteFailed' : 'errors.currencyDeleteFailed')),
    });
  }
}
