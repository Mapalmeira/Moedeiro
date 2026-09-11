import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal, untracked } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { Subscription, finalize, forkJoin } from 'rxjs';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { CashFlowPoint } from '../../../../core/ledgers/cash-flow.models';
import { CashFlowService } from '../../../../core/ledgers/cash-flow.service';
import { formatCurrencyAmount } from '../../../../core/ledgers/currency-format';
import { FinancialEvent } from '../../../../core/ledgers/financial-events.models';
import { FinancialEventsService } from '../../../../core/ledgers/financial-events.service';
import { LedgerBudgetOverview } from '../../../../core/ledgers/ledger-budgets.models';
import { LedgerBudgetsService } from '../../../../core/ledgers/ledger-budgets.service';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { flattenCategoryTree } from '../../../../core/ledgers/ledger-category-tree';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { LedgerAccount, LedgerAccountBalance, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../../core/ledgers/ledger-entities.service';
import { LedgerWorkspaceStateService } from '../../../../core/ledgers/ledger-workspace-state.service';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { EntityBadgeComponent } from '../../../../shared/ledger/entity-badge.component';
import { EntitySearchOption, EntitySearchSelectComponent } from '../../../../shared/ledger/entity-search-select.component';
import { FormMessageComponent } from '../../../../shared/ui/form-message.component';
import { IconComponent, IconName } from '../../../../shared/ui/icon.component';
import { financialEventPresentation } from '../../../../shared/ledger/financial-event-presentation';
import { PeriodSelectorComponent } from '../../../../shared/ui/period-selector.component';
import { currentMonthValue, dateInputTimestampRange, monthDateRange, monthTimestampRange, type PeriodMode } from '../../../../shared/period-selection';
import { DiscreteListCapacityDirective } from '../../../../shared/ui/discrete-list-capacity.directive';
import { HomeFlowChartComponent, HomeFlowMode, homeChartPointWidth } from './home-flow-chart.component';

type Tone = 'green' | 'yellow' | 'blue' | 'neutral';

interface HomeAccountRow {
  account: LedgerAccount;
  balance: string;
  balanceTone: 'positive' | 'negative' | 'neutral';
}

interface HomeBudgetRow {
  budget: LedgerBudgetOverview;
  account: LedgerAccount | null;
  category: LedgerCategory | null;
  spent: string;
  amount: string;
  percent: string;
  progress: number;
  tone: 'green' | 'yellow' | 'danger';
}

interface HomeEventRow {
  event: FinancialEvent;
  icon: IconName;
  tone: Tone;
  account: string;
  category: string;
  date: string;
  time: string;
  value: string;
  valueTone: 'positive' | 'negative' | 'neutral';
}


interface HomePreviewLimits {
  accounts: number;
  budgets: number;
  events: number;
}

const DAY_SECONDS = 86_400;
const HOME_PREVIEW_FETCH_LIMIT = 10;
const INITIAL_HOME_PREVIEW_LIMITS: HomePreviewLimits = { accounts: 5, budgets: 3, events: 4 };
const WARNING_BUDGET_USAGE_PERCENT = 80;

@Component({
  selector: 'app-ledger-home',
  host: { class: 'ui-workspace-page' },
  standalone: true,
  imports: [RouterLink, DiscreteListCapacityDirective, HomeFlowChartComponent, EntityBadgeComponent, EntitySearchSelectComponent, FormMessageComponent, IconComponent, PeriodSelectorComponent],
  templateUrl: './ledger-home.component.html',
  styleUrl: './ledger-home.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerHomeComponent {
  private readonly entities = inject(LedgerEntitiesService);
  private readonly categoriesService = inject(LedgerCategoriesService);
  private readonly eventsService = inject(FinancialEventsService);
  private readonly budgetsService = inject(LedgerBudgetsService);
  private readonly cashFlowService = inject(CashFlowService);
  private readonly errors = inject(ApiErrorService);
  private readonly workspaceState = inject(LedgerWorkspaceStateService);
  private readonly destroyRef = inject(DestroyRef);
  private resourcesRequest?: Subscription;
  private dashboardRequest?: Subscription;
  private chartRequest?: Subscription;
  private dashboardScopeKey: string | null = null;

  readonly context = inject(LedgerContextService);
  readonly i18n = inject(I18nService);
  private readonly dateFormatter = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: '2-digit', day: '2-digit' });
  private readonly timeFormatter = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  private readonly percentFormatter = new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 0 });

  readonly accounts = signal<LedgerAccount[]>([]);
  readonly currencies = signal<LedgerCurrency[]>([]);
  readonly categories = signal<LedgerCategory[]>([]);
  readonly balances = signal<LedgerAccountBalance[]>([]);
  readonly currencyBalance = signal(0);
  readonly cashFlowSummary = signal<CashFlowPoint | null>(null);
  readonly cashFlow = signal<CashFlowPoint[]>([]);
  readonly recentEvents = signal<FinancialEvent[]>([]);
  readonly activeBudgets = signal<LedgerBudgetOverview[]>([]);
  readonly selectedCurrencyUuid = signal('');
  readonly selectedFlowAccountUuid = signal('');
  readonly selectedMonth = signal(currentMonthValue());
  readonly periodMode = signal<PeriodMode>('month');
  readonly rangeFromDate = signal('');
  readonly rangeToDate = signal('');
  readonly flowMode = signal<HomeFlowMode>('instant');
  readonly resourcesReady = signal(false);
  readonly resourcesLoading = signal(false);
  readonly loading = signal(false);
  readonly flowLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly previewLimits = signal<HomePreviewLimits>(INITIAL_HOME_PREVIEW_LIMITS);


  private readonly accountByUuid = computed(() => new Map(this.accounts().map(account => [account.uuid, account] as const)));
  private readonly currencyByUuid = computed(() => new Map(this.currencies().map(currency => [currency.uuid, currency] as const)));
  private readonly categoryByUuid = computed(() => new Map(this.categories().map(category => [category.uuid, category] as const)));

  readonly currencyOptions = computed<EntitySearchOption[]>(() => this.currencies().map(currency => ({
    value: currency.uuid,
    label: currency.name,
    icon: currency.icon,
    color: currency.color_code,
  })));
  readonly flowAccountOptions = computed<EntitySearchOption[]>(() => [
    { value: '', label: this.i18n.t('activity.allAccounts'), uiIcon: 'building', tone: 'neutral' },
    ...this.accounts()
      .filter(account => account.currency_uuid === this.selectedCurrencyUuid())
      .map(account => ({
        value: account.uuid,
        label: account.name,
        detail: account.note,
        icon: account.icon,
        color: account.color_code,
      })),
  ]);
  readonly selectedCurrency = computed(() => this.currencyByUuid().get(this.selectedCurrencyUuid()) ?? null);
  readonly dashboardRange = computed(() => this.periodMode() === 'month' ? monthTimestampRange(this.selectedMonth()) : dateInputTimestampRange(this.rangeFromDate(), this.rangeToDate()));
  readonly invalidRange = computed(() => this.periodMode() === 'range' && !!this.rangeFromDate() && !!this.rangeToDate() && !this.dashboardRange());
  readonly totalIncome = computed(() => this.cashFlowSummary()?.income ?? 0);
  readonly totalExpense = computed(() => this.cashFlowSummary()?.expense ?? 0);
  readonly netFlow = computed(() => this.totalIncome() - this.totalExpense());
  readonly chartIncome = computed(() => this.cashFlow().reduce((sum, point) => sum + point.income, 0));
  readonly chartExpense = computed(() => this.cashFlow().reduce((sum, point) => sum + point.expense, 0));
  readonly metricCards = computed(() => {
    const currency = this.selectedCurrency();
    if (!currency) return [];
    return [
      { label: this.i18n.t('home.balance'), value: formatCurrencyAmount(this.currencyBalance(), currency), icon: 'wallet' as IconName, tone: 'green' as Tone },
      { label: this.i18n.t('home.income'), value: formatCurrencyAmount(this.totalIncome(), currency), icon: 'coins' as IconName, tone: 'blue' as Tone },
      { label: this.i18n.t('home.expense'), value: formatCurrencyAmount(this.totalExpense(), currency), icon: 'arrow-right' as IconName, tone: 'yellow' as Tone },
      { label: this.i18n.t('home.variation'), value: formatCurrencyAmount(this.netFlow(), currency), icon: 'chart' as IconName, tone: this.netFlow() < 0 ? 'yellow' as Tone : 'green' as Tone },
    ];
  });

  readonly accountRows = computed<HomeAccountRow[]>(() => {
    const currency = this.selectedCurrency();
    if (!currency) return [];
    const accounts = this.accountByUuid();
    return this.balances().flatMap<HomeAccountRow>(balance => {
      const account = accounts.get(balance.account_uuid);
      return account ? [{
        account,
        balance: formatCurrencyAmount(balance.balance, currency),
        balanceTone: balance.balance > 0 ? 'positive' : balance.balance < 0 ? 'negative' : 'neutral',
      }] : [];
    }).slice(0, this.previewLimits().accounts);
  });

  readonly budgetRows = computed<HomeBudgetRow[]>(() => {
    const currency = this.selectedCurrency();
    if (!currency) return [];
    const accounts = this.accountByUuid();
    const categories = this.categoryByUuid();
    return this.activeBudgets().map<HomeBudgetRow>(budget => {
      const spent = budget.spent_amount ?? 0;
      const usage = budget.amount === 0 ? (spent > 0 ? Number.POSITIVE_INFINITY : 0) : spent / budget.amount * 100;
      return {
        budget,
        account: accounts.get(budget.account_uuid) ?? null,
        category: categories.get(budget.category_uuid) ?? null,
        spent: formatCurrencyAmount(spent, currency),
        amount: formatCurrencyAmount(budget.amount, currency),
        percent: Number.isFinite(usage) ? this.percentFormatter.format(usage / 100) : '∞',
        progress: Number.isFinite(usage) ? Math.min(100, Math.max(0, usage)) : 100,
        tone: spent > budget.amount ? 'danger' : usage >= WARNING_BUDGET_USAGE_PERCENT ? 'yellow' : 'green',
      };
    }).slice(0, this.previewLimits().budgets);
  });

  readonly eventRows = computed<HomeEventRow[]>(() => {
    const currency = this.selectedCurrency();
    if (!currency) return [];
    const accountByUuid = this.accountByUuid();
    const categoryByUuid = this.categoryByUuid();
    return this.recentEvents().map<HomeEventRow>(event => {
      const movements = event.movements.filter(movement => accountByUuid.get(movement.account_uuid)?.currency_uuid === currency.uuid);
      const value = movements.reduce((sum, movement) => sum + movement.value * movement.quantity, 0);
      const accountNames = [...new Set(movements.map(movement => accountByUuid.get(movement.account_uuid)?.name).filter((name): name is string => !!name))];
      const categoryNames = [...new Set(movements.map(movement => categoryByUuid.get(movement.category_uuid)?.name).filter((name): name is string => !!name))];
      const presentation = financialEventPresentation(event.type);
      return {
        event,
        ...presentation,
        account: accountNames.join(', ') || this.i18n.t('home.unavailable'),
        category: categoryNames.length === 1 ? categoryNames[0] : categoryNames.length > 1 ? this.i18n.t('home.categoryCount', { count: categoryNames.length }) : this.i18n.t('home.unavailable'),
        date: this.dateFormatter.format(new Date(event.occurred_at * 1000)),
        time: this.timeFormatter.format(new Date(event.occurred_at * 1000)),
        value: formatCurrencyAmount(value, currency),
        valueTone: value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral',
      };
    }).slice(0, this.previewLimits().events);
  });


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
      const currencyUuid = this.selectedCurrencyUuid();
      const range = this.dashboardRange();
      const ready = this.resourcesReady();
      if (!ready) return;
      if (ledgerUuid && currencyUuid && range) {
        untracked(() => this.loadDashboard());
      } else {
        untracked(() => {
          this.dashboardRequest?.unsubscribe();
          this.clearDashboard();
          this.dashboardScopeKey = null;
          this.loading.set(false);
        });
      }
    });
    effect(() => {
      const ledgerUuid = this.context.ledgerUuid();
      const currencyUuid = this.selectedCurrencyUuid();
      const range = this.dashboardRange();
      const flowAccountUuid = this.selectedFlowAccountUuid();
      const ready = this.resourcesReady();
      if (!ready) return;
      if (ledgerUuid && currencyUuid && range) {
        untracked(() => this.loadChart(flowAccountUuid));
      } else {
        untracked(() => {
          this.chartRequest?.unsubscribe();
          this.clearChart();
          this.flowLoading.set(false);
        });
      }
    });
    this.destroyRef.onDestroy(() => {
      this.resourcesRequest?.unsubscribe();
      this.dashboardRequest?.unsubscribe();
      this.chartRequest?.unsubscribe();
    });
  }

  selectCurrency(value: string): void {
    if (value !== this.selectedCurrencyUuid()) {
      this.selectedCurrencyUuid.set(value);
      this.resetFlowAccountForCurrency();
      this.saveViewState();
    }
  }

  selectFlowAccount(value: string): void {
    if (value && !this.accounts().some(account => account.uuid === value && account.currency_uuid === this.selectedCurrencyUuid())) return;
    if (value !== this.selectedFlowAccountUuid()) {
      this.selectedFlowAccountUuid.set(value);
      this.saveViewState();
    }
  }

  selectMonth(value: string): void {
    if (/^\d{4}-\d{2}$/.test(value) && value !== this.selectedMonth()) {
      this.selectedMonth.set(value);
      this.saveViewState();
    }
  }

  setPeriodMode(mode: PeriodMode): void {
    if (mode === this.periodMode()) return;
    if (mode === 'range' && (!this.rangeFromDate() || !this.rangeToDate())) this.seedRangeFromMonth();
    this.periodMode.set(mode);
    this.saveViewState();
  }

  updateRangeFrom(value: string): void {
    this.rangeFromDate.set(value);
    this.saveViewState();
  }

  updateRangeTo(value: string): void {
    this.rangeToDate.set(value);
    this.saveViewState();
  }

  setFlowMode(mode: HomeFlowMode): void {
    if (mode === this.flowMode()) return;
    this.flowMode.set(mode);
    this.saveViewState();
  }

  setPreviewLimit(kind: keyof HomePreviewLimits, capacity: number): void {
    const current = this.previewLimits();
    if (current[kind] === capacity) return;
    this.previewLimits.set({ ...current, [kind]: capacity });
  }

  retry(): void {
    this.loadResources();
  }

  private loadResources(): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (!ledgerUuid) return;
    this.resourcesRequest?.unsubscribe();
    this.dashboardRequest?.unsubscribe();
    this.chartRequest?.unsubscribe();
    this.resourcesReady.set(false);
    this.resourcesLoading.set(true);
    this.loading.set(false);
    this.error.set(null);
    this.resourcesRequest = forkJoin({
      accounts: this.entities.listAccounts(ledgerUuid),
      currencies: this.entities.listCurrencies(ledgerUuid),
      categoryTree: this.categoriesService.getTree(ledgerUuid),
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: ({ accounts, currencies, categoryTree }) => {
        this.accounts.set(accounts);
        this.currencies.set(currencies);
        this.categories.set(flattenCategoryTree(categoryTree));
        const current = this.selectedCurrencyUuid();
        if (!currencies.some(currency => currency.uuid === current)) this.selectedCurrencyUuid.set(currencies[0]?.uuid ?? '');
        this.resetFlowAccountForCurrency();
        this.saveViewState();
        this.resourcesLoading.set(false);
        this.resourcesReady.set(true);
      },
      error: error => {
        this.resourcesLoading.set(false);
        this.error.set(this.errors.message(error, 'errors.homeLoadFailed'));
      },
    });
  }

  private loadDashboard(): void {
    const ledgerUuid = this.context.ledgerUuid();
    const currencyUuid = this.selectedCurrencyUuid();
    const range = this.dashboardRange();
    if (!ledgerUuid || !currencyUuid || !range) return;
    this.dashboardRequest?.unsubscribe();
    const scopeKey = `${ledgerUuid}/${currencyUuid}/${range.from}/${range.to}`;
    if (scopeKey !== this.dashboardScopeKey) {
      this.clearDashboard();
      this.dashboardScopeKey = scopeKey;
    }
    this.loading.set(true);
    this.error.set(null);
    const periodEndTimestamp = range.to - 1;
    this.dashboardRequest = forkJoin({
      balances: this.entities.listBalances(ledgerUuid, periodEndTimestamp, currencyUuid, HOME_PREVIEW_FETCH_LIMIT),
      cashFlowSummary: this.cashFlowService.summary(ledgerUuid, currencyUuid, {
        from_timestamp: range.from,
        to_timestamp: range.to,
        account_uuid: null,
        category_uuid: null,
        event_type: null,
      }),
      events: this.eventsService.list(ledgerUuid, {
        from_timestamp: range.from,
        to_timestamp: range.to,
        currency_uuid: currencyUuid,
        page_size: HOME_PREVIEW_FETCH_LIMIT,
        ascending: false,
      }),
      budgets: this.budgetsService.currencyOverview(ledgerUuid, currencyUuid, periodEndTimestamp, HOME_PREVIEW_FETCH_LIMIT),
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loading.set(false)),
    ).subscribe({
      next: ({ balances, cashFlowSummary, events, budgets }) => {
        this.balances.set(balances.items);
        this.currencyBalance.set(balances.total_balance ?? 0);
        this.cashFlowSummary.set(cashFlowSummary);
        this.recentEvents.set(events.events);
        this.activeBudgets.set(budgets);
      },
      error: error => this.error.set(this.errors.message(error, 'errors.homeLoadFailed')),
    });
  }

  private loadChart(flowAccountUuid: string): void {
    const ledgerUuid = this.context.ledgerUuid();
    const currencyUuid = this.selectedCurrencyUuid();
    const range = this.dashboardRange();
    if (!ledgerUuid || !currencyUuid || !range) return;
    this.chartRequest?.unsubscribe();
    this.clearChart();
    this.flowLoading.set(true);
    this.error.set(null);
    this.chartRequest = this.cashFlowService.points(
      ledgerUuid,
      currencyUuid,
      range.from,
      range.to,
      homeChartPointWidth(range),
      { account_uuid: flowAccountUuid || null },
    ).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.flowLoading.set(false)),
    ).subscribe({
      next: cashFlow => this.cashFlow.set(cashFlow),
      error: error => this.error.set(this.errors.message(error, 'errors.homeLoadFailed')),
    });
  }


  private seedRangeFromMonth(): void {
    const range = monthDateRange(this.selectedMonth());
    if (!range) return;
    this.rangeFromDate.set(range.from);
    this.rangeToDate.set(range.to);
  }

  private clearDashboard(): void {
    this.balances.set([]);
    this.currencyBalance.set(0);
    this.cashFlowSummary.set(null);
    this.recentEvents.set([]);
    this.activeBudgets.set([]);
  }

  private clearChart(): void {
    this.cashFlow.set([]);
  }

  private resetFlowAccountForCurrency(): void {
    const accountUuid = this.selectedFlowAccountUuid();
    if (accountUuid && !this.accounts().some(account => account.uuid === accountUuid && account.currency_uuid === this.selectedCurrencyUuid())) {
      this.selectedFlowAccountUuid.set('');
    }
  }


  private reset(ledgerUuid: string | null): void {
    this.resourcesRequest?.unsubscribe();
    this.dashboardRequest?.unsubscribe();
    this.chartRequest?.unsubscribe();
    this.accounts.set([]);
    this.currencies.set([]);
    this.categories.set([]);
    this.clearDashboard();
    this.clearChart();
    this.dashboardScopeKey = null;
    const saved = ledgerUuid ? this.workspaceState.getHome(ledgerUuid) : null;
    this.selectedCurrencyUuid.set(saved?.currency_uuid ?? '');
    this.selectedFlowAccountUuid.set(saved?.flow_account_uuid ?? '');
    this.selectedMonth.set(saved?.month ?? currentMonthValue());
    this.periodMode.set(saved?.period_mode ?? 'month');
    this.rangeFromDate.set(saved?.range_from_date ?? '');
    this.rangeToDate.set(saved?.range_to_date ?? '');
    this.flowMode.set(saved?.flow_mode ?? 'instant');
    this.resourcesReady.set(false);
    this.resourcesLoading.set(false);
    this.loading.set(false);
    this.flowLoading.set(false);
    this.error.set(null);
  }

  private saveViewState(): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (!ledgerUuid) return;
    this.workspaceState.setHome(ledgerUuid, {
      currency_uuid: this.selectedCurrencyUuid(),
      flow_account_uuid: this.selectedFlowAccountUuid(),
      month: this.selectedMonth(),
      period_mode: this.periodMode(),
      range_from_date: this.rangeFromDate(),
      range_to_date: this.rangeToDate(),
      flow_mode: this.flowMode(),
    });
  }
}
