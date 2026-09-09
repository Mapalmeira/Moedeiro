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
import { I18nService } from '../../../../core/i18n/i18n.service';
import { nextDateInput, zonedDateInput, zonedDateTimeToEpochSeconds } from '../../../../core/preferences/date-time-format';
import { PreferencesService } from '../../../../core/preferences/preferences.service';
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
  private readonly destroyRef = inject(DestroyRef);
  private resourcesRequest?: Subscription;
  private graphRequest?: Subscription;

  readonly context = inject(LedgerContextService);
  readonly preferences = inject(PreferencesService);
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

  readonly locale = computed(() => this.i18n.language() === 'en' ? 'en-US' : 'pt-BR');
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
        this.reset();
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
    if (value !== this.selectedAccountUuid()) this.selectedAccountUuid.set(value);
  }

  setPeriodMode(mode: PeriodMode): void {
    if (mode === this.periodMode()) return;
    if (mode === 'range' && (!this.rangeFromDate() || !this.rangeToDate())) this.seedRangeFromMonth();
    this.periodMode.set(mode);
  }

  selectMonth(value: string): void {
    if (/^\d{4}-\d{2}$/.test(value) && value !== this.selectedMonth()) this.selectedMonth.set(value);
  }

  setRangeFromDate(value: string): void {
    this.rangeFromDate.set(value);
  }

  setRangeToDate(value: string): void {
    this.rangeToDate.set(value);
  }

  updateDetailLevel(event: Event): void {
    const value = Number((event.target as HTMLInputElement).value);
    if (Number.isInteger(value) && value >= 1 && value <= MAX_CATEGORY_DETAIL_LEVEL) this.detailLevel.set(value);
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
    return currency ? formatCurrencyAmount(value, currency, this.preferences.current().number_format) : '—';
  }

  private monthRange(month: string): TimestampRange | null {
    const match = /^(\d{4})-(\d{2})$/.exec(month);
    if (!match) return null;
    const year = Number(match[1]);
    const monthNumber = Number(match[2]);
    if (monthNumber < 1 || monthNumber > 12) return null;
    const nextYear = monthNumber === 12 ? year + 1 : year;
    const nextMonth = monthNumber === 12 ? 1 : monthNumber + 1;
    const timezone = this.preferences.current().timezone;
    const from = zonedDateTimeToEpochSeconds(`${String(year).padStart(4, '0')}-${String(monthNumber).padStart(2, '0')}-01`, '00:00:00', timezone);
    const to = zonedDateTimeToEpochSeconds(`${String(nextYear).padStart(4, '0')}-${String(nextMonth).padStart(2, '0')}-01`, '00:00:00', timezone);
    return from === null || to === null ? null : { from, to };
  }

  private customRange(): TimestampRange | null {
    const fromDate = this.rangeFromDate();
    const nextToDate = nextDateInput(this.rangeToDate());
    if (!fromDate || !nextToDate) return null;
    const timezone = this.preferences.current().timezone;
    const from = zonedDateTimeToEpochSeconds(fromDate, '00:00:00', timezone);
    const to = zonedDateTimeToEpochSeconds(nextToDate, '00:00:00', timezone);
    return from === null || to === null || from >= to ? null : { from, to };
  }

  private seedRangeFromMonth(): void {
    const range = this.monthRange(this.selectedMonth());
    if (!range) return;
    const timezone = this.preferences.current().timezone;
    this.rangeFromDate.set(zonedDateInput(range.from, timezone));
    this.rangeToDate.set(zonedDateInput(range.to - 1, timezone));
  }

  private currentMonth(): string {
    return zonedDateInput(Math.floor(Date.now() / 1000), this.preferences.current().timezone).slice(0, 7);
  }

  private reset(): void {
    this.resourcesRequest?.unsubscribe();
    this.graphRequest?.unsubscribe();
    this.accounts.set([]);
    this.currencies.set([]);
    this.selectedAccountUuid.set('');
    this.selectedMonth.set(this.currentMonth());
    this.periodMode.set('month');
    this.rangeFromDate.set('');
    this.rangeToDate.set('');
    this.detailLevel.set(DEFAULT_CATEGORY_DETAIL_LEVEL);
    this.graph.set(null);
    this.resourcesReady.set(false);
    this.resourcesLoading.set(false);
    this.loading.set(false);
    this.error.set(null);
  }
}
