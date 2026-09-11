import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { DialogShellComponent } from '../../../shared/ui/dialog-shell.component';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Observable, Subscription, finalize, forkJoin, map } from 'rxjs';
import { ApiErrorService } from '../../../core/api/api-error';
import { I18nService } from '../../../core/i18n/i18n.service';
import { formatCurrencyAmount } from '../../../core/ledgers/currency-format';
import { LedgerAccount, LedgerAccountBalance, LedgerCurrency } from '../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../core/ledgers/ledger-entities.service';
import { LedgerContextService } from '../../../core/ledgers/ledger-context.service';
import { LedgerWorkspaceStateService } from '../../../core/ledgers/ledger-workspace-state.service';
import { EntityBadgeComponent } from '../../../shared/ledger/entity-badge.component';
import { normalizeSearchText } from '../../../shared/search-normalization';
import { FormMessageComponent } from '../../../shared/ui/form-message.component';
import { IconComponent } from '../../../shared/ui/icon.component';
import { EntityEditorComponent } from './entity-editor.component';

type Kind = 'account' | 'currency';
type Entity = LedgerAccount | LedgerCurrency;

@Component({
  selector: 'app-ledger-entity-manager',
  imports: [DialogShellComponent, IconComponent, EntityBadgeComponent, FormMessageComponent, EntityEditorComponent],
  templateUrl: './ledger-entity-manager.component.html',
  styleUrl: './ledger-entity-manager.component.scss',
  host: { '[class.currency-section]': "kind() === 'currency'" },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerEntityManagerComponent {
  private readonly entities = inject(LedgerEntitiesService);
  readonly context = inject(LedgerContextService);
  private readonly workspaceState = inject(LedgerWorkspaceStateService);
  private readonly errors = inject(ApiErrorService);
  private readonly destroyRef = inject(DestroyRef);
  private request?: Subscription;

  readonly i18n = inject(I18nService);
  readonly kind = input.required<Kind>();
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly items = signal<Entity[]>([]);
  readonly currencies = signal<LedgerCurrency[]>([]);
  readonly balances = signal<LedgerAccountBalance[]>([]);
  private readonly currencyByUuid = computed(() => new Map(this.currencies().map(currency => [currency.uuid, currency] as const)));
  private readonly balanceByAccountUuid = computed(() => new Map(this.balances().map(balance => [balance.account_uuid, balance.balance] as const)));
  private readonly balanceByCurrencyUuid = computed(() => {
    const totals = new Map<string, number>();
    for (const balance of this.balances()) totals.set(balance.currency_uuid, (totals.get(balance.currency_uuid) ?? 0) + balance.balance);
    return totals;
  });
  readonly search = signal('');
  readonly editorOpen = signal(false);
  readonly editing = signal<Entity | null>(null);
  readonly deleting = signal<Entity | null>(null);
  readonly deletingBusy = signal(false);
  readonly deleteError = signal<string | null>(null);
  readonly filtered = computed(() => {
    const query = normalizeSearchText(this.search().trim());
    return this.items().filter(item => normalizeSearchText(item.name).includes(query));
  });
  readonly rows = computed(() => this.filtered().map(item => {
    const currency = 'currency_uuid' in item ? this.currencyByUuid().get(item.currency_uuid) ?? null : item;
    const balance = 'currency_uuid' in item
      ? this.balanceByAccountUuid().get(item.uuid) ?? 0
      : this.balanceByCurrencyUuid().get(item.uuid) ?? 0;
    return {
      item,
      detailText: 'currency_uuid' in item ? item.note : null,
      balance,
      balanceText: currency ? formatCurrencyAmount(balance, currency) : null,
    };
  }));
  readonly title = computed(() => this.i18n.t(this.kind() === 'account' ? 'ledgerShell.accounts' : 'ledgerShell.currencies'));

  constructor() {
    effect(() => {
      const uuid = this.context.ledgerUuid();
      this.kind();
      untracked(() => {
        this.search.set(uuid ? this.workspaceState.getEntitySearch(uuid, this.kind()) ?? '' : '');
        this.editorOpen.set(false);
        this.editing.set(null);
        this.deleting.set(null);
        if (uuid) this.load();
      });
    });
    this.destroyRef.onDestroy(() => this.request?.unsubscribe());
  }

  filter(event: Event): void {
    const search = (event.target as HTMLInputElement).value;
    this.search.set(search);
    const ledgerUuid = this.context.ledgerUuid();
    if (ledgerUuid) this.workspaceState.setEntitySearch(ledgerUuid, this.kind(), search);
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
    const timestamp = Math.floor(Date.now() / 1000);
    const request: Observable<{ items: Entity[]; currencies: LedgerCurrency[]; balances: LedgerAccountBalance[] }> = this.kind() === 'account'
      ? forkJoin({ accounts: this.entities.listAccounts(uuid), currencies: this.entities.listCurrencies(uuid), balanceList: this.entities.listBalances(uuid, timestamp) }).pipe(
          map(({ accounts, currencies, balanceList }) => ({ items: accounts, currencies, balances: balanceList.items })),
        )
      : forkJoin({ currencies: this.entities.listCurrencies(uuid), balanceList: this.entities.listBalances(uuid, timestamp) }).pipe(
          map(({ currencies, balanceList }) => ({ items: currencies, currencies, balances: balanceList.items })),
        );
    this.request = request.pipe(finalize(() => this.loading.set(false))).subscribe({
      next: ({ items, currencies, balances }) => {
        this.items.set(items);
        this.currencies.set(currencies);
        this.balances.set(balances);
      },
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
