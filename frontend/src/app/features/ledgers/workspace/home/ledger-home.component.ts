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
import { LedgerCategory, LedgerCategoryTreeNode } from '../../../../core/ledgers/ledger-categories.models';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { LedgerAccount, LedgerAccountBalance, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../../core/ledgers/ledger-entities.service';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { formatEventDate, formatEventTime, zonedDateInput, zonedDateTimeToEpochSeconds } from '../../../../core/preferences/date-time-format';
import { PreferencesService } from '../../../../core/preferences/preferences.service';
import { EntityBadgeComponent } from '../../../../shared/ledger/entity-badge.component';
import { EntitySearchOption, EntitySearchSelectComponent } from '../../../../shared/ledger/entity-search-select.component';
import { FormMessageComponent } from '../../../../shared/ui/form-message.component';
import { IconComponent, IconName } from '../../../../shared/ui/icon.component';
import { MonthSelectComponent } from '../../../../shared/ui/month-select.component';

type FlowMode = 'instant' | 'cumulative';
type PeriodMode = 'month' | 'range';
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

interface ChartPointView {
  index: number;
  x: number;
  xPercent: number;
  barWidth: number;
  barGap: number;
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

const DAY_SECONDS = 86_400;
const RECENT_EVENT_COUNT = 4;
const ACTIVE_BUDGET_COUNT = 3;
const HOME_ACCOUNT_COUNT = 5;
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
const CHART_BAR_WIDTH_RATIO = .38;
const CHART_BAR_GAP_RATIO = .05;
const CHART_MIN_BAR_WIDTH = .25;
const CHART_MAX_BAR_WIDTH = 16;
const CHART_MAX_BAR_GAP = 1;

@Component({
  selector: 'app-ledger-home',
  standalone: true,
  imports: [RouterLink, EntityBadgeComponent, EntitySearchSelectComponent, FormMessageComponent, IconComponent, MonthSelectComponent],
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
  private readonly destroyRef = inject(DestroyRef);
  private resourcesRequest?: Subscription;
  private dashboardRequest?: Subscription;

  readonly context = inject(LedgerContextService);
  readonly preferences = inject(PreferencesService);
  readonly i18n = inject(I18nService);

  readonly accounts = signal<LedgerAccount[]>([]);
  readonly currencies = signal<LedgerCurrency[]>([]);
  readonly categories = signal<LedgerCategory[]>([]);
  readonly balances = signal<LedgerAccountBalance[]>([]);
  readonly currencyBalance = signal(0);
  readonly cashFlow = signal<CashFlowPoint[]>([]);
  readonly recentEvents = signal<FinancialEvent[]>([]);
  readonly activeBudgets = signal<LedgerBudgetOverview[]>([]);
  readonly selectedCurrencyUuid = signal('');
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
  readonly error = signal<string | null>(null);

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

  readonly locale = computed(() => this.i18n.language() === 'en' ? 'en-US' : 'pt-BR');
  readonly currencyOptions = computed<EntitySearchOption[]>(() => this.currencies().map(currency => ({
    value: currency.uuid,
    label: currency.name,
    icon: currency.icon,
    color: currency.color_code,
  })));
  readonly selectedCurrency = computed(() => this.currencyByUuid().get(this.selectedCurrencyUuid()) ?? null);
  readonly dashboardRange = computed(() => this.periodMode() === 'month' ? this.monthRange(this.selectedMonth()) : this.customRange());
  readonly totalIncome = computed(() => this.cashFlow().reduce((sum, point) => sum + point.income, 0));
  readonly totalExpense = computed(() => this.cashFlow().reduce((sum, point) => sum + point.expense, 0));
  readonly netFlow = computed(() => this.totalIncome() - this.totalExpense());
  readonly metricCards = computed(() => {
    const currency = this.selectedCurrency();
    if (!currency) return [];
    const numberFormat = this.preferences.current().number_format;
    return [
      { label: this.i18n.t('home.balance'), value: formatCurrencyAmount(this.currencyBalance(), currency, numberFormat), icon: 'wallet' as IconName, tone: 'green' as Tone },
      { label: this.i18n.t('home.income'), value: formatCurrencyAmount(this.totalIncome(), currency, numberFormat), icon: 'coins' as IconName, tone: 'blue' as Tone },
      { label: this.i18n.t('home.expense'), value: formatCurrencyAmount(this.totalExpense(), currency, numberFormat), icon: 'arrow-right' as IconName, tone: 'yellow' as Tone },
      { label: this.i18n.t('home.netFlow'), value: formatCurrencyAmount(this.netFlow(), currency, numberFormat), icon: 'chart' as IconName, tone: this.netFlow() < 0 ? 'yellow' as Tone : 'green' as Tone },
    ];
  });

  readonly accountRows = computed<HomeAccountRow[]>(() => {
    const currency = this.selectedCurrency();
    if (!currency) return [];
    const accounts = this.accountByUuid();
    const numberFormat = this.preferences.current().number_format;
    return this.balances().flatMap(balance => {
      const account = accounts.get(balance.account_uuid);
      return account ? [{
        account,
        balance: formatCurrencyAmount(balance.balance, currency, numberFormat),
        balanceTone: balance.balance > 0 ? 'positive' : balance.balance < 0 ? 'negative' : 'neutral',
      }] : [];
    });
  });

  readonly budgetRows = computed<HomeBudgetRow[]>(() => {
    const currency = this.selectedCurrency();
    if (!currency) return [];
    const accounts = this.accountByUuid();
    const categories = this.categoryByUuid();
    const format = this.preferences.current().number_format;
    return this.activeBudgets().map(budget => {
      const spent = budget.spent_amount ?? 0;
      const usage = budget.amount === 0 ? (spent > 0 ? Number.POSITIVE_INFINITY : 0) : spent / budget.amount * 100;
      return {
        budget,
        account: accounts.get(budget.account_uuid) ?? null,
        category: categories.get(budget.category_uuid) ?? null,
        spent: formatCurrencyAmount(spent, currency, format),
        amount: formatCurrencyAmount(budget.amount, currency, format),
        percent: Number.isFinite(usage) ? `${new Intl.NumberFormat(this.locale(), { maximumFractionDigits: 0 }).format(usage)}%` : '∞',
        progress: Number.isFinite(usage) ? Math.min(100, Math.max(0, usage)) : 100,
        tone: spent > budget.amount ? 'danger' : usage >= WARNING_BUDGET_USAGE_PERCENT ? 'yellow' : 'green',
      };
    });
  });

  readonly eventRows = computed<HomeEventRow[]>(() => {
    const currency = this.selectedCurrency();
    if (!currency) return [];
    const accountByUuid = this.accountByUuid();
    const categoryByUuid = this.categoryByUuid();
    const preferences = this.preferences.current();
    return this.recentEvents().map(event => {
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
        date: formatEventDate(event.occurred_at, preferences.timezone, preferences.date_format),
        time: formatEventTime(event.occurred_at, preferences.timezone, preferences.time_format),
        value: formatCurrencyAmount(value, currency, preferences.number_format),
        valueTone: value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral',
      };
    });
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
    const barGap = Math.min(CHART_MAX_BAR_GAP, slot * CHART_BAR_GAP_RATIO);
    const labelStride = Math.max(1, Math.ceil(points.length / CHART_X_LABEL_TARGET_COUNT));
    const currency = this.selectedCurrency();
    const preferences = this.preferences.current();
    const range = this.dashboardRange();
    if (!currency || !range) return [];
    return points.map((point, index) => {
      const x = CHART_LEFT + slot * index + slot / 2;
      const incomeHeight = point.income * scale;
      const expenseHeight = point.expense * scale;
      const cumulativeValue = cumulative[index] ?? 0;
      const pointTimestamp = range.from + index * DAY_SECONDS;
      const pointDateInput = zonedDateInput(pointTimestamp, preferences.timezone);
      const day = String(Number(pointDateInput.slice(8, 10)));
      const shortDate = this.i18n.language() === 'en'
        ? `${pointDateInput.slice(5, 7)}/${pointDateInput.slice(8, 10)}`
        : `${pointDateInput.slice(8, 10)}/${pointDateInput.slice(5, 7)}`;
      return {
        index,
        x,
        xPercent: Math.min(86, Math.max(14, x / CHART_WIDTH * 100)),
        barWidth,
        barGap,
        incomeY: CHART_ZERO_Y - incomeHeight,
        incomeHeight,
        expenseHeight,
        cumulativeY: CHART_ZERO_Y - cumulativeValue * scale,
        label: this.periodMode() === 'month' ? day : shortDate,
        showLabel: index === 0 || index === points.length - 1 || (index % labelStride === 0 && points.length - 1 - index >= labelStride),
        date: formatEventDate(pointTimestamp, preferences.timezone, preferences.date_format),
        income: formatCurrencyAmount(point.income, currency, preferences.number_format),
        expense: formatCurrencyAmount(point.expense, currency, preferences.number_format),
        net: formatCurrencyAmount(point.income - point.expense, currency, preferences.number_format),
        cumulative: formatCurrencyAmount(cumulativeValue, currency, preferences.number_format),
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
        this.reset();
        if (ledgerUuid) this.loadResources();
      });
    });
    effect(() => {
      const ledgerUuid = this.context.ledgerUuid();
      const currencyUuid = this.selectedCurrencyUuid();
      const range = this.dashboardRange();
      const ready = this.resourcesReady();
      if (ledgerUuid && currencyUuid && range && ready) untracked(() => this.loadDashboard());
    });
    this.destroyRef.onDestroy(() => {
      this.resourcesRequest?.unsubscribe();
      this.dashboardRequest?.unsubscribe();
    });
  }

  selectCurrency(value: string): void {
    if (value !== this.selectedCurrencyUuid()) this.selectedCurrencyUuid.set(value);
  }

  selectMonth(value: string): void {
    if (/^\d{4}-\d{2}$/.test(value) && value !== this.selectedMonth()) this.selectedMonth.set(value);
  }

  setPeriodMode(mode: PeriodMode): void {
    if (mode === this.periodMode()) return;
    if (mode === 'range' && (!this.rangeFromDate() || !this.rangeToDate())) this.seedRangeFromMonth();
    this.periodMode.set(mode);
  }

  updateRangeFrom(event: Event): void {
    this.rangeFromDate.set((event.target as HTMLInputElement).value);
  }

  updateRangeTo(event: Event): void {
    this.rangeToDate.set((event.target as HTMLInputElement).value);
  }

  setFlowMode(mode: FlowMode): void {
    if (mode === this.flowMode()) return;
    this.flowMode.set(mode);
    this.hoveredChartIndex.set(null);
    this.pinnedChartIndex.set(null);
  }

  hoverChart(event: PointerEvent): void {
    if (event.pointerType && event.pointerType !== 'mouse') return;
    this.hoveredChartIndex.set(this.chartIndexAt(event));
  }

  leaveChart(): void {
    this.hoveredChartIndex.set(null);
  }

  pinChart(event: MouseEvent): void {
    const index = this.chartIndexAt(event);
    if (index === null) return;
    this.pinnedChartIndex.update(current => current === index ? null : index);
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
    this.loading.set(true);
    this.error.set(null);
    this.hoveredChartIndex.set(null);
    this.pinnedChartIndex.set(null);
    const now = Math.floor(Date.now() / 1000);
    const balanceTimestamp = Math.min(now, range.to - 1);
    this.dashboardRequest = forkJoin({
      balances: this.entities.listBalances(ledgerUuid, balanceTimestamp, currencyUuid, HOME_ACCOUNT_COUNT),
      cashFlow: this.cashFlowService.points(ledgerUuid, currencyUuid, range.from, range.to, DAY_SECONDS),
      events: this.eventsService.list(ledgerUuid, {
        from_timestamp: range.from,
        to_timestamp: range.to,
        currency_uuid: currencyUuid,
        page_size: RECENT_EVENT_COUNT,
        ascending: false,
      }),
      budgets: this.budgetsService.currencyOverview(ledgerUuid, currencyUuid, ACTIVE_BUDGET_COUNT),
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loading.set(false)),
    ).subscribe({
      next: ({ balances, cashFlow, events, budgets }) => {
        this.balances.set(balances.items);
        this.currencyBalance.set(balances.total_balance ?? 0);
        this.cashFlow.set(cashFlow);
        this.recentEvents.set(events.events);
        this.activeBudgets.set(budgets);
      },
      error: error => this.error.set(this.errors.message(error, 'errors.homeLoadFailed')),
    });
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
      ? new Intl.NumberFormat(this.locale(), { notation: 'compact', maximumFractionDigits: 1 }).format(major)
      : new Intl.NumberFormat(this.locale(), { maximumSignificantDigits: 4 }).format(major);
  }

  private monthRange(month: string): { from: number; to: number } | null {
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


  private customRange(): { from: number; to: number } | null {
    const fromDate = this.rangeFromDate();
    const toDate = this.rangeToDate();
    const nextToDate = this.nextDateInput(toDate);
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

  private nextDateInput(value: string): string | null {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!match) return null;
    const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
    if (Number.isNaN(date.getTime())) return null;
    date.setUTCDate(date.getUTCDate() + 1);
    return `${String(date.getUTCFullYear()).padStart(4, '0')}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`;
  }

  private currentMonth(): string {
    const timezone = this.preferences.current().timezone;
    return zonedDateInput(Math.floor(Date.now() / 1000), timezone).slice(0, 7);
  }

  private flattenCategories(nodes: readonly LedgerCategoryTreeNode[]): LedgerCategory[] {
    return nodes.flatMap(node => [node.category, ...this.flattenCategories(node.children)]);
  }

  private eventPresentation(type: FinancialEvent['type']): { icon: IconName; tone: Tone } {
    if (type === 'ACCOUNT_TRANSFER') return { icon: 'arrow-left-right', tone: 'blue' };
    if (type === 'SHOPPING_LIST') return { icon: 'coins', tone: 'yellow' };
    return { icon: 'wallet', tone: 'green' };
  }

  private reset(): void {
    this.resourcesRequest?.unsubscribe();
    this.dashboardRequest?.unsubscribe();
    this.accounts.set([]);
    this.currencies.set([]);
    this.categories.set([]);
    this.balances.set([]);
    this.currencyBalance.set(0);
    this.cashFlow.set([]);
    this.recentEvents.set([]);
    this.activeBudgets.set([]);
    this.selectedCurrencyUuid.set('');
    this.selectedMonth.set(this.currentMonth());
    this.periodMode.set('month');
    this.rangeFromDate.set('');
    this.rangeToDate.set('');
    this.flowMode.set('instant');
    this.hoveredChartIndex.set(null);
    this.pinnedChartIndex.set(null);
    this.resourcesReady.set(false);
    this.resourcesLoading.set(false);
    this.loading.set(false);
    this.error.set(null);
  }
}
