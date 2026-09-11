import { formatDate } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal, untracked } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subscription, finalize, forkJoin } from 'rxjs';
import { ApiErrorService } from '../../../../core/api/api-error';
import { CashFlowSankey } from '../../../../core/ledgers/cash-flow.models';
import { CashFlowService } from '../../../../core/ledgers/cash-flow.service';
import { formatCurrencyAmount } from '../../../../core/ledgers/currency-format';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { LedgerAccount, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../../core/ledgers/ledger-entities.service';
import { LedgerWorkspaceStateService } from '../../../../core/ledgers/ledger-workspace-state.service';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { EntitySearchOption, EntitySearchSelectComponent } from '../../../../shared/ledger/entity-search-select.component';
import { FormMessageComponent } from '../../../../shared/ui/form-message.component';
import { IconComponent } from '../../../../shared/ui/icon.component';
import { PeriodMode, PeriodSelectorComponent } from '../../../../shared/ui/period-selector.component';
import { CashFlowSankeyComponent } from './cash-flow-sankey.component';

interface TimestampRange {
  from: number;
  to: number;
}

const MAX_CATEGORY_DETAIL_LEVEL = 5;
const DEFAULT_CATEGORY_DETAIL_LEVEL = 3;

@Component({
  selector: 'app-ledger-flows',
  host: { class: 'ui-workspace-page' },
  standalone: true,
  imports: [CashFlowSankeyComponent, EntitySearchSelectComponent, FormMessageComponent, IconComponent, PeriodSelectorComponent],
  templateUrl: './ledger-flows.component.html',
  styleUrl: './ledger-flows.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerFlowsComponent {
  private readonly entities = inject(LedgerEntitiesService);
  private readonly cashFlow = inject(CashFlowService);
  private readonly errors = inject(ApiErrorService);
  private readonly workspaceState = inject(LedgerWorkspaceStateService);
  private readonly destroyRef = inject(DestroyRef);
  private resourcesRequest?: Subscription;
  private graphRequest?: Subscription;

  readonly context = inject(LedgerContextService);
  readonly i18n = inject(I18nService);

  readonly accounts = signal<LedgerAccount[]>([]);
  readonly currencies = signal<LedgerCurrency[]>([]);
  readonly selectedAccountUuid = signal('');
  readonly selectedMonth = signal(this.currentMonth());
  readonly periodMode = signal<PeriodMode>('month');
  readonly rangeFromDate = signal('');
  readonly rangeToDate = signal('');
  readonly detailLevel = signal(DEFAULT_CATEGORY_DETAIL_LEVEL);
  readonly detailLevels = Array.from({ length: MAX_CATEGORY_DETAIL_LEVEL }, (_, index) => index + 1);
  readonly graph = signal<CashFlowSankey | null>(null);
  readonly resourcesReady = signal(false);
  readonly resourcesLoading = signal(false);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  private readonly accountByUuid = computed(() => new Map(this.accounts().map(account => [account.uuid, account] as const)));
  private readonly currencyByUuid = computed(() => new Map(this.currencies().map(currency => [currency.uuid, currency] as const)));

  readonly accountOptions = computed<EntitySearchOption[]>(() => this.accounts().map(account => ({
    value: account.uuid,
    label: account.name,
    detail: account.note,
    icon: account.icon,
    color: account.color_code,
  })));
  readonly selectedAccount = computed(() => this.accountByUuid().get(this.selectedAccountUuid()) ?? null);
  readonly selectedCurrency = computed(() => {
    const account = this.selectedAccount();
    return account ? this.currencyByUuid().get(account.currency_uuid) ?? null : null;
  });
  readonly selectedRange = computed<TimestampRange | null>(() => this.periodMode() === 'month' ? this.monthRange(this.selectedMonth()) : this.customRange());
  readonly invalidRange = computed(() => this.periodMode() === 'range' && !!this.rangeFromDate() && !!this.rangeToDate() && !this.selectedRange());
  readonly incomeLabel = computed(() => this.formatAmount(this.graph()?.income ?? 0));
  readonly expenseLabel = computed(() => this.formatAmount(this.graph()?.expense ?? 0));

  constructor() {
    effect(() => {
      const ledgerUuid = this.context.ledgerUuid();
      untracked(() => {
        this.reset(ledgerUuid);
        if (ledgerUuid) this.loadResources();
      });
    });
    effect(() => {
      const ledgerUuid = this.context.ledgerUuid();
      const accountUuid = this.selectedAccountUuid();
      const range = this.selectedRange();
      const detailLevel = this.detailLevel();
      const ready = this.resourcesReady();
      if (!ready) return;
      if (!ledgerUuid || !accountUuid || !range) {
        untracked(() => {
          this.graphRequest?.unsubscribe();
          this.graph.set(null);
          this.loading.set(false);
        });
        return;
      }
      untracked(() => this.loadGraph());
    });
    this.destroyRef.onDestroy(() => {
      this.resourcesRequest?.unsubscribe();
      this.graphRequest?.unsubscribe();
    });
  }

  selectAccount(value: string): void {
    if (value !== this.selectedAccountUuid()) {
      this.selectedAccountUuid.set(value);
      this.saveViewState();
    }
  }

  setPeriodMode(mode: PeriodMode): void {
    if (mode === this.periodMode()) return;
    if (mode === 'range' && (!this.rangeFromDate() || !this.rangeToDate())) this.seedRangeFromMonth();
    this.periodMode.set(mode);
    this.saveViewState();
  }

  selectMonth(value: string): void {
    if (/^\d{4}-\d{2}$/.test(value) && value !== this.selectedMonth()) {
      this.selectedMonth.set(value);
      this.saveViewState();
    }
  }

  setRangeFromDate(value: string): void {
    this.rangeFromDate.set(value);
    this.saveViewState();
  }

  setRangeToDate(value: string): void {
    this.rangeToDate.set(value);
    this.saveViewState();
  }

  updateDetailLevel(event: Event): void {
    const value = Number((event.target as HTMLInputElement).value);
    if (Number.isInteger(value) && value >= 1 && value <= MAX_CATEGORY_DETAIL_LEVEL) {
      this.detailLevel.set(value);
      this.saveViewState();
    }
  }

  retry(): void {
    if (this.resourcesReady()) this.loadGraph();
    else this.loadResources();
  }

  private loadResources(): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (!ledgerUuid) return;
    this.resourcesRequest?.unsubscribe();
    this.graphRequest?.unsubscribe();
    this.resourcesReady.set(false);
    this.resourcesLoading.set(true);
    this.loading.set(false);
    this.error.set(null);
    this.resourcesRequest = forkJoin({
      accounts: this.entities.listAccounts(ledgerUuid),
      currencies: this.entities.listCurrencies(ledgerUuid),
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.resourcesLoading.set(false)),
    ).subscribe({
      next: ({ accounts, currencies }) => {
        this.accounts.set(accounts);
        this.currencies.set(currencies);
        const selected = this.selectedAccountUuid();
        if (!accounts.some(account => account.uuid === selected)) this.selectedAccountUuid.set(accounts[0]?.uuid ?? '');
        this.saveViewState();
        this.resourcesReady.set(true);
      },
      error: error => this.error.set(this.errors.message(error, 'errors.flowsLoadFailed')),
    });
  }

  private loadGraph(): void {
    const ledgerUuid = this.context.ledgerUuid();
    const accountUuid = this.selectedAccountUuid();
    const range = this.selectedRange();
    if (!ledgerUuid || !accountUuid || !range) return;
    this.graphRequest?.unsubscribe();
    this.graph.set(null);
    this.loading.set(true);
    this.error.set(null);
    this.graphRequest = this.cashFlow.sankey(ledgerUuid, accountUuid, range.from, range.to, this.detailLevel()).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loading.set(false)),
    ).subscribe({
      next: graph => this.graph.set(graph),
      error: error => this.error.set(this.errors.message(error, 'errors.flowsLoadFailed')),
    });
  }

  private formatAmount(value: number): string {
    const currency = this.selectedCurrency();
    return currency ? formatCurrencyAmount(value, currency) : '—';
  }

  private monthRange(month: string): TimestampRange | null {
    const match = /^(\d{4})-(\d{2})$/.exec(month);
    if (!match) return null;
    const year = Number(match[1]);
    const monthNumber = Number(match[2]);
    if (monthNumber < 1 || monthNumber > 12) return null;
    const from = Math.floor(new Date(year, monthNumber - 1, 1).getTime() / 1000);
    const to = Math.floor(new Date(year, monthNumber, 1).getTime() / 1000);
    return { from, to };
  }

  private customRange(): TimestampRange | null {
    const fromInput = this.rangeFromDate();
    const toInput = this.rangeToDate();
    const fromDate = new Date(`${fromInput}T00:00:00`);
    const toDate = new Date(`${toInput}T00:00:00`);
    if (Number.isNaN(fromDate.getTime()) || Number.isNaN(toDate.getTime())
        || formatDate(fromDate, 'yyyy-MM-dd', 'en-US') !== fromInput
        || formatDate(toDate, 'yyyy-MM-dd', 'en-US') !== toInput) return null;
    toDate.setDate(toDate.getDate() + 1);
    const from = Math.floor(fromDate.getTime() / 1000);
    const to = Math.floor(toDate.getTime() / 1000);
    return from >= to ? null : { from, to };
  }

  private seedRangeFromMonth(): void {
    const range = this.monthRange(this.selectedMonth());
    if (!range) return;
    this.rangeFromDate.set(formatDate(range.from * 1000, 'yyyy-MM-dd', 'en-US'));
    this.rangeToDate.set(formatDate((range.to - 1) * 1000, 'yyyy-MM-dd', 'en-US'));
  }

  private currentMonth(): string {
    return formatDate(Date.now(), 'yyyy-MM', 'en-US');
  }

  private reset(ledgerUuid: string | null): void {
    this.resourcesRequest?.unsubscribe();
    this.graphRequest?.unsubscribe();
    this.accounts.set([]);
    this.currencies.set([]);
    const saved = ledgerUuid ? this.workspaceState.getFlows(ledgerUuid) : null;
    this.selectedAccountUuid.set(saved?.account_uuid ?? '');
    this.selectedMonth.set(saved?.month ?? this.currentMonth());
    this.periodMode.set(saved?.period_mode ?? 'month');
    this.rangeFromDate.set(saved?.range_from_date ?? '');
    this.rangeToDate.set(saved?.range_to_date ?? '');
    this.detailLevel.set(saved?.detail_level ?? DEFAULT_CATEGORY_DETAIL_LEVEL);
    this.graph.set(null);
    this.resourcesReady.set(false);
    this.resourcesLoading.set(false);
    this.loading.set(false);
    this.error.set(null);
  }

  private saveViewState(): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (!ledgerUuid) return;
    this.workspaceState.setFlows(ledgerUuid, {
      account_uuid: this.selectedAccountUuid(),
      month: this.selectedMonth(),
      period_mode: this.periodMode(),
      range_from_date: this.rangeFromDate(),
      range_to_date: this.rangeToDate(),
      detail_level: this.detailLevel(),
    });
  }
}
