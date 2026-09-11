import { formatDate } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, HostListener, computed, effect, inject, signal, untracked, viewChild } from '@angular/core';
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
import { LedgerCategory, LedgerCategoryTreeNode } from '../../../../core/ledgers/ledger-categories.models';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { LedgerAccount, LedgerAccountBalance, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../../core/ledgers/ledger-entities.service';
import { LedgerWorkspaceStateService } from '../../../../core/ledgers/ledger-workspace-state.service';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { EntityBadgeComponent } from '../../../../shared/ledger/entity-badge.component';
import { EntitySearchOption, EntitySearchSelectComponent } from '../../../../shared/ledger/entity-search-select.component';
import { FormMessageComponent } from '../../../../shared/ui/form-message.component';
import { IconComponent, IconName } from '../../../../shared/ui/icon.component';
import { PeriodMode, PeriodSelectorComponent } from '../../../../shared/ui/period-selector.component';

type FlowMode = 'instant' | 'cumulative';
type Tone = 'green' | 'yellow' | 'blue' | 'neutral';
type ChartDateLabelDetail = 'day' | 'month' | 'year';

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

interface ChartPointView {
  index: number;
  x: number;
  xPercent: number;
  barWidth: number;
  incomeX: number;
  expenseX: number;
  incomeY: number;
  incomeHeight: number;
  expenseHeight: number;
  cumulativeY: number;
  label: string;
  showLabel: boolean;
  date: string;
  income: string;
  expense: string;
  net: string;
  cumulative: string;
}

interface ChartTickView {
  y: number;
  label: string;
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
const CHART_WIDTH = 1000;
const CHART_HEIGHT = 300;
const CHART_LEFT = 118;
const CHART_RIGHT = 28;
const CHART_TOP = 20;
const CHART_BOTTOM = 48;
const CHART_PLOT_WIDTH = CHART_WIDTH - CHART_LEFT - CHART_RIGHT;
const CHART_PLOT_HEIGHT = CHART_HEIGHT - CHART_TOP - CHART_BOTTOM;
const CHART_ZERO_Y = CHART_TOP + CHART_PLOT_HEIGHT / 2;
const CHART_X_LABEL_TARGET_COUNT = 10;
const CHART_X_LABEL_WITH_YEAR_TARGET_COUNT = 6;
const CHART_MAX_POINTS = 100;
const CHART_BAR_WIDTH_RATIO = .38;
const CHART_MIN_BAR_WIDTH = .25;
const CHART_MAX_BAR_WIDTH = 16;

@Component({
  selector: 'app-ledger-home',
  host: { class: 'ui-workspace-page' },
  standalone: true,
  imports: [RouterLink, EntityBadgeComponent, EntitySearchSelectComponent, FormMessageComponent, IconComponent, PeriodSelectorComponent],
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
  private previewObserver?: ResizeObserver;
  private previewContentObserver?: MutationObserver;
  private dashboardScopeKey: string | null = null;

  readonly context = inject(LedgerContextService);
  readonly i18n = inject(I18nService);
  private readonly dateFormatter = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: '2-digit', day: '2-digit' });
  private readonly timeFormatter = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  private readonly percentFormatter = new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 0 });
  private readonly chartDateFormatters: Record<ChartDateLabelDetail, Intl.DateTimeFormat> = {
    day: new Intl.DateTimeFormat(undefined, { day: 'numeric' }),
    month: new Intl.DateTimeFormat(undefined, { day: '2-digit', month: '2-digit' }),
    year: new Intl.DateTimeFormat(undefined, { day: '2-digit', month: '2-digit', year: 'numeric' }),
  };

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
  readonly selectedMonth = signal(this.currentMonth());
  readonly periodMode = signal<PeriodMode>('month');
  readonly rangeFromDate = signal('');
  readonly rangeToDate = signal('');
  readonly flowMode = signal<FlowMode>('instant');
  readonly hoveredChartIndex = signal<number | null>(null);
  readonly pinnedChartIndex = signal<number | null>(null);
  readonly resourcesReady = signal(false);
  readonly resourcesLoading = signal(false);
  readonly loading = signal(false);
  readonly flowLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly previewLimits = signal<HomePreviewLimits>(INITIAL_HOME_PREVIEW_LIMITS);

  readonly accountsList = viewChild<ElementRef<HTMLElement>>('accountsList');
  readonly budgetList = viewChild<ElementRef<HTMLElement>>('budgetList');
  readonly eventsList = viewChild<ElementRef<HTMLElement>>('eventsList');

  readonly chartWidth = CHART_WIDTH;
  readonly chartHeight = CHART_HEIGHT;
  readonly chartLeft = CHART_LEFT;
  readonly chartRight = CHART_WIDTH - CHART_RIGHT;
  readonly chartTop = CHART_TOP;
  readonly chartBottom = CHART_HEIGHT - CHART_BOTTOM;
  readonly chartZeroY = CHART_ZERO_Y;

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
  readonly dashboardRange = computed(() => this.periodMode() === 'month' ? this.monthRange(this.selectedMonth()) : this.customRange());
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
      const presentation = this.eventPresentation(event.type);
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

  readonly cumulativeValues = computed(() => {
    const values: number[] = [];
    let running = 0;
    for (const point of this.cashFlow()) {
      running += point.income - point.expense;
      values.push(running);
    }
    return values;
  });

  readonly chartScale = computed(() => {
    const values = this.flowMode() === 'instant'
      ? this.cashFlow().flatMap(point => [point.income, point.expense])
      : this.cumulativeValues().map(value => Math.abs(value));
    return Math.max(1, ...values);
  });

  readonly chartTicks = computed<ChartTickView[]>(() => {
    const max = this.chartScale();
    return [1, .5, 0, -.5, -1].map(factor => ({
      y: CHART_ZERO_Y - factor * (CHART_PLOT_HEIGHT / 2),
      label: this.formatChartTick(max * factor),
    }));
  });

  readonly chartPoints = computed<ChartPointView[]>(() => {
    const points = this.cashFlow();
    const cumulative = this.cumulativeValues();
    const max = this.chartScale();
    const scale = (CHART_PLOT_HEIGHT / 2) / max;
    const slot = CHART_PLOT_WIDTH / Math.max(1, points.length);
    const barWidth = Math.max(CHART_MIN_BAR_WIDTH, Math.min(CHART_MAX_BAR_WIDTH, slot * CHART_BAR_WIDTH_RATIO));
    const currency = this.selectedCurrency();
    const range = this.dashboardRange();
    if (!currency || !range) return [];
    const labelDetail: ChartDateLabelDetail = this.periodMode() === 'range'
      ? this.chartDateLabelDetail(range)
      : 'day';
    const labelTargetCount = labelDetail === 'year' ? CHART_X_LABEL_WITH_YEAR_TARGET_COUNT : CHART_X_LABEL_TARGET_COUNT;
    const labelStride = Math.max(1, Math.ceil(points.length / labelTargetCount));
    const labelOffset = Math.floor(labelStride / 2);
    const pointWidth = this.chartPointWidth(range);
    return points.map((point, index) => {
      const x = CHART_LEFT + slot * index + slot / 2;
      const incomeHeight = point.income * scale;
      const expenseHeight = point.expense * scale;
      const cumulativeValue = cumulative[index] ?? 0;
      const pointTimestamp = range.from + index * pointWidth;
      const shortDate = this.chartDateLabel(pointTimestamp, labelDetail);
      return {
        index,
        x,
        xPercent: Math.min(86, Math.max(14, x / CHART_WIDTH * 100)),
        barWidth,
        incomeX: x - barWidth / 2,
        expenseX: x - barWidth / 2,
        incomeY: CHART_ZERO_Y - incomeHeight,
        incomeHeight,
        expenseHeight,
        cumulativeY: CHART_ZERO_Y - cumulativeValue * scale,
        label: shortDate,
        showLabel: index % labelStride === labelOffset,
        date: this.dateFormatter.format(new Date(pointTimestamp * 1000)),
        income: formatCurrencyAmount(point.income, currency),
        expense: formatCurrencyAmount(point.expense, currency),
        net: formatCurrencyAmount(point.income - point.expense, currency),
        cumulative: formatCurrencyAmount(cumulativeValue, currency),
      };
    });
  });

  readonly cumulativePolyline = computed(() => this.chartPoints().map(point => `${point.x},${point.cumulativeY}`).join(' '));
  readonly activeChartPoint = computed(() => {
    const index = this.pinnedChartIndex() ?? this.hoveredChartIndex();
    return index === null ? null : this.chartPoints()[index] ?? null;
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
      const accountsList = this.accountsList();
      const budgetList = this.budgetList();
      const eventsList = this.eventsList();
      untracked(() => this.observePreviewCapacity(accountsList, budgetList, eventsList));
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
      this.previewObserver?.disconnect();
      this.previewContentObserver?.disconnect();
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

  setFlowMode(mode: FlowMode): void {
    if (mode === this.flowMode()) return;
    this.flowMode.set(mode);
    this.hoveredChartIndex.set(null);
    this.pinnedChartIndex.set(null);
    this.saveViewState();
  }

  hoverChart(event: PointerEvent): void {
    if (event.pointerType && event.pointerType !== 'mouse') return;
    this.pinnedChartIndex.set(null);
    this.hoveredChartIndex.set(this.chartIndexAt(event));
  }

  leaveChart(): void {
    this.hoveredChartIndex.set(null);
  }

  pinChart(event: PointerEvent): void {
    if (event.pointerType === 'mouse') return;
    const index = this.chartIndexAt(event);
    if (index === null) return;
    this.pinnedChartIndex.update(current => current === index ? null : index);
  }

  keepChartSelection(event: PointerEvent): void {
    event.stopPropagation();
  }

  @HostListener('document:pointerdown')
  clearChartSelectionOnOutsidePointerDown(): void {
    this.clearChartSelection();
  }

  moveChartSelection(delta: number, event: Event): void {
    const points = this.chartPoints();
    if (!points.length) return;
    event.preventDefault();
    const current = this.pinnedChartIndex() ?? this.hoveredChartIndex() ?? (delta > 0 ? -1 : points.length);
    this.pinnedChartIndex.set(Math.max(0, Math.min(points.length - 1, current + delta)));
    this.hoveredChartIndex.set(null);
  }

  clearChartSelection(): void {
    this.hoveredChartIndex.set(null);
    this.pinnedChartIndex.set(null);
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
        this.categories.set(this.flattenCategories(categoryTree));
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
      this.chartPointWidth(range),
      { account_uuid: flowAccountUuid || null },
    ).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.flowLoading.set(false)),
    ).subscribe({
      next: cashFlow => this.cashFlow.set(cashFlow),
      error: error => this.error.set(this.errors.message(error, 'errors.homeLoadFailed')),
    });
  }

  private chartPointWidth(range: { from: number; to: number }): number {
    const days = (range.to - range.from) / DAY_SECONDS;
    return Math.max(1, Math.ceil(days / CHART_MAX_POINTS)) * DAY_SECONDS;
  }

  private chartDateLabelDetail(range: { from: number; to: number }): ChartDateLabelDetail {
    const fromDate = formatDate(range.from * 1000, 'yyyy-MM-dd', 'en-US');
    const toDate = formatDate((range.to - 1) * 1000, 'yyyy-MM-dd', 'en-US');
    if (fromDate.slice(0, 4) !== toDate.slice(0, 4)) return 'year';
    if (fromDate.slice(0, 7) !== toDate.slice(0, 7)) return 'month';
    return 'day';
  }

  private chartDateLabel(timestampSeconds: number, detail: ChartDateLabelDetail): string {
    return this.chartDateFormatters[detail].format(new Date(timestampSeconds * 1000));
  }

  private chartIndexAt(event: MouseEvent | PointerEvent): number | null {
    const target = event.currentTarget;
    if (!(target instanceof SVGSVGElement)) return null;
    const points = this.chartPoints();
    if (!points.length) return null;
    const bounds = target.getBoundingClientRect();
    if (bounds.width <= 0) return null;
    const x = (event.clientX - bounds.left) / bounds.width * CHART_WIDTH;
    const slot = CHART_PLOT_WIDTH / points.length;
    const raw = Math.round((x - CHART_LEFT - slot / 2) / slot);
    return Math.max(0, Math.min(points.length - 1, raw));
  }

  private formatChartTick(value: number): string {
    const currency = this.selectedCurrency();
    if (!currency) return String(value);
    const major = value / 10 ** currency.decimal_places;
    return Math.abs(major) >= 1000
      ? new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(major)
      : new Intl.NumberFormat(undefined, { maximumSignificantDigits: 4 }).format(major);
  }

  private monthRange(month: string): { from: number; to: number } | null {
    const match = /^(\d{4})-(\d{2})$/.exec(month);
    if (!match) return null;
    const year = Number(match[1]);
    const monthNumber = Number(match[2]);
    if (monthNumber < 1 || monthNumber > 12) return null;
    const from = Math.floor(new Date(year, monthNumber - 1, 1).getTime() / 1000);
    const to = Math.floor(new Date(year, monthNumber, 1).getTime() / 1000);
    return { from, to };
  }


  private customRange(): { from: number; to: number } | null {
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

  private flattenCategories(nodes: readonly LedgerCategoryTreeNode[]): LedgerCategory[] {
    return nodes.flatMap(node => [node.category, ...this.flattenCategories(node.children)]);
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
    this.hoveredChartIndex.set(null);
    this.pinnedChartIndex.set(null);
  }

  private resetFlowAccountForCurrency(): void {
    const accountUuid = this.selectedFlowAccountUuid();
    if (accountUuid && !this.accounts().some(account => account.uuid === accountUuid && account.currency_uuid === this.selectedCurrencyUuid())) {
      this.selectedFlowAccountUuid.set('');
    }
  }

  private observePreviewCapacity(
    accountsList: ElementRef<HTMLElement> | undefined,
    budgetList: ElementRef<HTMLElement> | undefined,
    eventsList: ElementRef<HTMLElement> | undefined,
  ): void {
    this.previewObserver?.disconnect();
    this.previewContentObserver?.disconnect();
    if (!accountsList || !budgetList || !eventsList) return;

    const lists = [accountsList.nativeElement, budgetList.nativeElement, eventsList.nativeElement] as const;
    const resize = () => this.updatePreviewCapacity(...lists);
    if (typeof ResizeObserver !== 'undefined') {
      this.previewObserver = new ResizeObserver(resize);
      lists.forEach(list => this.previewObserver?.observe(list));
    }
    if (typeof MutationObserver !== 'undefined') {
      this.previewContentObserver = new MutationObserver(resize);
      lists.forEach(list => this.previewContentObserver?.observe(list, { childList: true }));
    }
    resize();
  }

  private updatePreviewCapacity(accountsList: HTMLElement, budgetList: HTMLElement, eventsList: HTMLElement): void {
    this.setPreviewLimits({
      accounts: this.previewCapacity(accountsList),
      budgets: this.previewCapacity(budgetList),
      events: this.previewCapacity(eventsList),
    });
  }

  private previewCapacity(list: HTMLElement): number {
    const row = list.querySelector<HTMLElement>(':scope > a');
    const rowHeight = row ? Number.parseFloat(getComputedStyle(row).minHeight) : Number.NaN;
    const listHeight = list.getBoundingClientRect().height;
    return Number.isFinite(rowHeight) && rowHeight > 0 && listHeight > 0
      ? Math.min(HOME_PREVIEW_FETCH_LIMIT, Math.max(1, Math.floor(listHeight / rowHeight)))
      : 1;
  }

  private setPreviewLimits(next: HomePreviewLimits): void {
    const current = this.previewLimits();
    if (current.accounts !== next.accounts || current.budgets !== next.budgets || current.events !== next.events) this.previewLimits.set(next);
  }

  private eventPresentation(type: FinancialEvent['type']): { icon: IconName; tone: Tone } {
    if (type === 'ACCOUNT_TRANSFER') return { icon: 'arrow-left-right', tone: 'blue' };
    if (type === 'SHOPPING_LIST') return { icon: 'coins', tone: 'yellow' };
    return { icon: 'wallet', tone: 'green' };
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
    this.selectedMonth.set(saved?.month ?? this.currentMonth());
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
