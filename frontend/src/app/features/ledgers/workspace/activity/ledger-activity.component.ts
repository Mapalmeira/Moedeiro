import { ChangeDetectionStrategy, Component, DestroyRef, HostListener, computed, effect, inject, signal, untracked } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';
import { Subscription, finalize, forkJoin } from 'rxjs';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { CashFlowPoint } from '../../../../core/ledgers/cash-flow.models';
import { CashFlowService } from '../../../../core/ledgers/cash-flow.service';
import { LedgerCategory, LedgerCategoryTreeNode } from '../../../../core/ledgers/ledger-categories.models';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { formatCurrencyAmount } from '../../../../core/ledgers/currency-format';
import { LedgerAccount, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../../core/ledgers/ledger-entities.service';
import { FinancialEvent, FinancialEventFilters, FinancialEventType } from '../../../../core/ledgers/financial-events.models';
import { FinancialEventsService } from '../../../../core/ledgers/financial-events.service';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { LedgerWorkspaceStateService } from '../../../../core/ledgers/ledger-workspace-state.service';
import { formatEventDate, formatEventTime, zonedDateInput, zonedDateTimeToEpochSeconds } from '../../../../core/preferences/date-time-format';
import { PreferencesService } from '../../../../core/preferences/preferences.service';
import { EntityBadgeComponent } from '../../../../shared/ledger/entity-badge.component';
import { EntitySearchOption, EntitySearchSelectComponent } from '../../../../shared/ledger/entity-search-select.component';
import { FormMessageComponent } from '../../../../shared/ui/form-message.component';
import { IconComponent, IconName } from '../../../../shared/ui/icon.component';
import { InfiniteScrollTriggerDirective } from '../../../../shared/ui/infinite-scroll-trigger.directive';
import { PeriodMode, PeriodSelectorComponent } from '../../../../shared/ui/period-selector.component';
import { FinancialEventEditorComponent } from './financial-event-editor.component';

const EVENT_BATCH_SIZE = 40;

type ActivityEventTone = 'green' | 'yellow' | 'blue';
type ActivityValueTone = 'negative' | 'positive' | 'neutral';

interface ActivityEventRow {
  event: FinancialEvent;
  date: string;
  time: string;
  detail: string | null;
  typeLabel: string;
  typeIcon: IconName;
  tone: ActivityEventTone;
  accounts: LedgerAccount[];
  accountLabel: string;
  categoryPreview: LedgerCategory[];
  categoryLabel: string;
  value: string;
  valueTone: ActivityValueTone;
}

@Component({
  selector: 'app-ledger-activity',
  host: { class: 'ui-workspace-page' },
  standalone: true,
  imports: [ReactiveFormsModule, FinancialEventEditorComponent, EntityBadgeComponent, EntitySearchSelectComponent, FormMessageComponent, IconComponent, InfiniteScrollTriggerDirective, PeriodSelectorComponent],
  templateUrl: './ledger-activity.component.html',
  styleUrl: './ledger-activity.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerActivityComponent {
  private readonly fb = inject(FormBuilder);
  private readonly eventsService = inject(FinancialEventsService);
  private readonly entitiesService = inject(LedgerEntitiesService);
  private readonly categoriesService = inject(LedgerCategoriesService);
  private readonly cashFlowService = inject(CashFlowService);
  private readonly errors = inject(ApiErrorService);
  private readonly preferences = inject(PreferencesService);
  private readonly workspaceState = inject(LedgerWorkspaceStateService);
  private readonly destroyRef = inject(DestroyRef);
  private workspaceRequest?: Subscription;
  private eventsRequest?: Subscription;
  private moreRequest?: Subscription;
  private balanceRequest?: Subscription;
  private summaryRequest?: Subscription;
  readonly context = inject(LedgerContextService);
  readonly i18n = inject(I18nService);
  readonly categoryIconPreviewLimit = 2;
  readonly periodMode = signal<PeriodMode>('month');
  readonly selectedMonth = signal(this.currentMonth());
  readonly locale = computed(() => this.i18n.language() === 'en' ? 'en-US' : 'pt-BR');

  readonly accounts = signal<LedgerAccount[]>([]);
  readonly currencies = signal<LedgerCurrency[]>([]);
  readonly categoryTree = signal<LedgerCategoryTreeNode[]>([]);
  readonly events = signal<FinancialEvent[]>([]);
  readonly totalEventCount = signal(0);
  readonly loading = signal(false);
  readonly loadingMore = signal(false);
  readonly error = signal<string | null>(null);
  readonly filterError = signal<string | null>(null);
  readonly nextCursor = signal<string | null>(null);
  readonly appliedFilters = signal<Omit<FinancialEventFilters, 'cursor'> | null>(null);
  readonly createMenuOpen = signal(false);
  readonly editorType = signal<FinancialEventType | null>(null);
  readonly editingEvent = signal<FinancialEvent | null>(null);
  readonly deleting = signal<FinancialEvent | null>(null);
  readonly deletingBusy = signal(false);
  readonly deleteError = signal<string | null>(null);
  readonly accountBalance = signal<number | null>(null);
  readonly balanceLoading = signal(false);
  readonly balanceUnavailable = signal(false);
  readonly cashFlowSummary = signal<CashFlowPoint | null>(null);
  readonly summaryLoading = signal(false);
  readonly summaryUnavailable = signal(false);

  readonly filters = this.fb.nonNullable.group({
    from_date: [''],
    to_date: [''],
    account_uuid: [''],
    category_uuid: [''],
    description_search: [''],
  });

  readonly categories = computed(() => this.flattenCategories(this.categoryTree()));
  readonly categoryPaths = computed(() => {
    const paths = new Map<string, string>();
    const visit = (nodes: readonly LedgerCategoryTreeNode[], parentPath: string): void => {
      for (const node of nodes) {
        const path = parentPath ? `${parentPath} › ${node.category.name}` : node.category.name;
        paths.set(node.category.uuid, path);
        visit(node.children, path);
      }
    };
    visit(this.categoryTree(), '');
    return paths;
  });
  readonly accountByUuid = computed(() => new Map(this.accounts().map(account => [account.uuid, account] as const)));
  readonly categoryByUuid = computed(() => new Map(this.categories().map(category => [category.uuid, category] as const)));
  readonly currencyByUuid = computed(() => new Map(this.currencies().map(currency => [currency.uuid, currency] as const)));
  readonly accountFilterOptions = computed<readonly EntitySearchOption[]>(() => [
    { value: '', label: this.i18n.t('activity.allAccounts'), uiIcon: 'building', tone: 'neutral' },
    ...this.accounts().map(account => ({
      value: account.uuid,
      label: account.name,
      detail: this.currencyByUuid().get(account.currency_uuid)?.name ?? null,
      icon: account.icon,
      color: account.color_code,
    })),
  ]);
  readonly categoryFilterOptions = computed<readonly EntitySearchOption[]>(() => [
    { value: '', label: this.i18n.t('categories.root'), uiIcon: 'folder', tone: 'neutral' },
    ...this.categories().map(category => {
      const path = this.categoryPaths().get(category.uuid) ?? category.name;
      return {
        value: category.uuid,
        label: category.name,
        detail: path === category.name ? null : path,
        icon: category.icon,
        color: category.color_code,
      };
    }),
  ]);
  readonly canCreate = computed(() => this.accounts().length > 0 && this.categories().length > 0);
  readonly appliedAccount = computed(() => {
    const accountUuid = this.appliedFilters()?.account_uuid;
    return accountUuid ? this.accountByUuid().get(accountUuid) ?? null : null;
  });
  readonly formattedAccountBalance = computed(() => {
    const account = this.appliedAccount();
    const balance = this.accountBalance();
    if (!account || balance === null) return null;
    const currency = this.currencyByUuid().get(account.currency_uuid);
    return currency ? formatCurrencyAmount(balance, currency, this.preferences.current().number_format) : null;
  });
  readonly accountBalanceTone = computed<ActivityValueTone>(() => {
    const balance = this.accountBalance();
    return balance === null ? 'neutral' : balance < 0 ? 'negative' : balance > 0 ? 'positive' : 'neutral';
  });
  readonly formattedCashFlowSummary = computed(() => {
    const account = this.appliedAccount();
    const summary = this.cashFlowSummary();
    if (!account || !summary) return null;
    const currency = this.currencyByUuid().get(account.currency_uuid);
    if (!currency) return null;
    const numberFormat = this.preferences.current().number_format;
    const variation = summary.income - summary.expense;
    return {
      income: formatCurrencyAmount(summary.income, currency, numberFormat),
      expense: formatCurrencyAmount(summary.expense, currency, numberFormat),
      variation: formatCurrencyAmount(variation, currency, numberFormat),
      variationTone: variation < 0 ? 'negative' as ActivityValueTone : variation > 0 ? 'positive' as ActivityValueTone : 'neutral' as ActivityValueTone,
    };
  });
  readonly eventRows = computed<readonly ActivityEventRow[]>(() => {
    const preferences = this.preferences.current();
    const accountByUuid = this.accountByUuid();
    const currencyByUuid = this.currencyByUuid();
    const categoryByUuid = this.categoryByUuid();
    const categoryPaths = this.categoryPaths();

    return this.events().map(event => {
      const accountUuids = [...new Set(event.movements.map(movement => movement.account_uuid))];
      const categoryUuids = [...new Set(event.movements.map(movement => movement.category_uuid))];
      const accounts = accountUuids.map(uuid => accountByUuid.get(uuid)).filter((account): account is LedgerAccount => !!account);
      const categories = categoryUuids.map(uuid => categoryByUuid.get(uuid)).filter((category): category is LedgerCategory => !!category);
      const accountLabel = accountUuids.map(uuid => accountByUuid.get(uuid)?.name ?? this.i18n.t('activity.unknownAccount')).join(', ');
      const categoryLabel = categoryUuids.length === 1
        ? categoryPaths.get(categoryUuids[0]) ?? this.i18n.t('activity.unknownCategory')
        : this.i18n.t('activity.multipleCategories', { count: categoryUuids.length });

      let detail: string | null = null;
      if (event.type === 'SHOPPING_LIST') {
        detail = this.i18n.t('activity.movementCount', { count: event.movements.length });
      } else if (event.type === 'ACCOUNT_TRANSFER') {
        const destination = event.movements.find(movement => movement.value > 0) ?? null;
        const fee = destination ? event.movements.find(movement => movement.value < 0 && movement.account_uuid === destination.account_uuid) ?? null : null;
        if (fee) {
          const feeCurrencyUuid = accountByUuid.get(fee.account_uuid)?.currency_uuid;
          const feeCurrency = feeCurrencyUuid ? currencyByUuid.get(feeCurrencyUuid) ?? null : null;
          detail = feeCurrency
            ? this.i18n.t('activity.transferFeeDetail', { value: formatCurrencyAmount(Math.abs(fee.value * fee.quantity), feeCurrency, preferences.number_format) })
            : this.i18n.t('activity.transferWithFee');
        }
      }

      const aggregateMovements = this.aggregateMovements(event);
      const aggregateCurrencyUuids = new Set(aggregateMovements
        .map(movement => accountByUuid.get(movement.account_uuid)?.currency_uuid)
        .filter((uuid): uuid is string => !!uuid));
      const aggregateCurrencies = [...aggregateCurrencyUuids]
        .map(uuid => currencyByUuid.get(uuid))
        .filter((currency): currency is LedgerCurrency => !!currency);
      let value = this.i18n.t('activity.differentCurrencies');
      let valueTone: ActivityValueTone = 'neutral';
      if (aggregateCurrencies.length === 1) {
        const total = aggregateMovements.reduce((sum, movement) => sum + (movement.value * movement.quantity), 0);
        value = formatCurrencyAmount(total, aggregateCurrencies[0], preferences.number_format);
        valueTone = total < 0 ? 'negative' : total > 0 ? 'positive' : 'neutral';
      }

      return {
        event,
        date: formatEventDate(event.occurred_at, preferences.timezone, preferences.date_format),
        time: formatEventTime(event.occurred_at, preferences.timezone, preferences.time_format),
        detail,
        typeLabel: this.eventTypeLabel(event.type),
        typeIcon: this.eventIcon(event.type),
        tone: this.eventTone(event.type),
        accounts,
        accountLabel,
        categoryPreview: categories.slice(0, this.categoryIconPreviewLimit),
        categoryLabel,
        value,
        valueTone,
      };
    });
  });

  constructor() {
    this.filters.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.saveFilters());
    effect(() => {
      const ledgerUuid = this.context.ledgerUuid();
      untracked(() => {
        this.workspaceRequest?.unsubscribe();
        this.eventsRequest?.unsubscribe();
        this.moreRequest?.unsubscribe();
        this.balanceRequest?.unsubscribe();
        this.summaryRequest?.unsubscribe();
        this.restoreFilters(ledgerUuid);
        this.resetTransientState();
        if (ledgerUuid) this.loadWorkspace();
      });
    });
    this.destroyRef.onDestroy(() => {
      this.workspaceRequest?.unsubscribe();
      this.eventsRequest?.unsubscribe();
      this.moreRequest?.unsubscribe();
      this.balanceRequest?.unsubscribe();
      this.summaryRequest?.unsubscribe();
    });
  }

  @HostListener('document:click')
  closeMenus(): void {
    this.createMenuOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  closeMenusOnEscape(): void {
    this.createMenuOpen.set(false);
  }

  toggleCreateMenu(event: Event): void {
    event.stopPropagation();
    this.createMenuOpen.update(open => !open);
  }

  openCreate(type: FinancialEventType, event: Event): void {
    event.stopPropagation();
    this.createMenuOpen.set(false);
    this.editingEvent.set(null);
    this.editorType.set(type);
  }

  openEdit(event: FinancialEvent): void {
    this.editingEvent.set(event);
    this.editorType.set(event.type);
  }

  openEditFromKeyboard(keyboardEvent: KeyboardEvent, event: FinancialEvent): void {
    if (keyboardEvent.key !== 'Enter' && keyboardEvent.key !== ' ') return;
    keyboardEvent.preventDefault();
    this.openEdit(event);
  }

  requestDeleteFromEditor(event: FinancialEvent): void {
    this.closeEditor();
    this.confirmDelete(event);
  }

  closeEditor(): void {
    this.editorType.set(null);
    this.editingEvent.set(null);
  }

  editorSaved(): void {
    this.closeEditor();
    this.loadEvents();
  }

  applyFilters(): void {
    this.loadEvents();
  }

  clearFilters(): void {
    this.resetFilters();
    this.loadEvents();
  }

  setFilterValue(name: 'account_uuid' | 'category_uuid', value: string): void {
    this.filters.controls[name].setValue(value);
    this.filters.controls[name].markAsDirty();
  }

  setPeriodMode(mode: PeriodMode): void {
    if (mode === this.periodMode()) return;
    this.periodMode.set(mode);
    if (mode === 'month') this.syncMonthToFilters();
  }

  selectMonth(value: string): void {
    if (!/^\d{4}-\d{2}$/.test(value) || value === this.selectedMonth()) return;
    this.selectedMonth.set(value);
    if (this.periodMode() === 'month') this.syncMonthToFilters();
  }

  setRangeDate(name: 'from_date' | 'to_date', value: string): void {
    this.filters.controls[name].setValue(value);
    this.filters.controls[name].markAsDirty();
  }

  loadMore(): void {
    const cursor = this.nextCursor();
    const ledgerUuid = this.context.ledgerUuid();
    const applied = this.appliedFilters();
    if (!cursor || !ledgerUuid || !applied || this.loadingMore()) return;
    this.loadingMore.set(true);
    this.moreRequest?.unsubscribe();
    this.moreRequest = this.eventsService.list(ledgerUuid, { ...applied, cursor }).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loadingMore.set(false)),
    ).subscribe({
      next: page => {
        this.events.update(current => [...current, ...page.events]);
        this.nextCursor.set(page.next_cursor);
        this.totalEventCount.set(page.total_count);
      },
      error: error => this.error.set(this.errors.message(error, 'errors.financialEventsLoadFailed')),
    });
  }

  confirmDelete(event: FinancialEvent, clickEvent?: Event): void {
    clickEvent?.stopPropagation();
    this.deleteError.set(null);
    this.deleting.set(event);
  }

  closeDelete(): void {
    if (!this.deletingBusy()) this.deleting.set(null);
  }

  remove(): void {
    const event = this.deleting();
    const ledgerUuid = this.context.ledgerUuid();
    if (!event || !ledgerUuid || this.deletingBusy()) return;
    this.deletingBusy.set(true);
    this.deleteError.set(null);
    this.eventsService.delete(ledgerUuid, event.uuid).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.deletingBusy.set(false)),
    ).subscribe({
      next: () => {
        this.deleting.set(null);
        this.loadEvents();
      },
      error: error => this.deleteError.set(this.errors.message(error, 'errors.financialEventDeleteFailed')),
    });
  }

  private eventTypeLabel(type: FinancialEventType): string {
    if (type === 'SHOPPING_LIST') return this.i18n.t('activity.typeShopping');
    if (type === 'ACCOUNT_TRANSFER') return this.i18n.t('activity.typeTransfer');
    return this.i18n.t('activity.typeSimple');
  }

  private eventIcon(type: FinancialEventType): IconName {
    if (type === 'SHOPPING_LIST') return 'shopping-cart';
    if (type === 'ACCOUNT_TRANSFER') return 'arrow-left-right';
    return 'wallet';
  }

  private eventTone(type: FinancialEventType): ActivityEventTone {
    if (type === 'SHOPPING_LIST') return 'yellow';
    if (type === 'ACCOUNT_TRANSFER') return 'blue';
    return 'green';
  }

  private loadWorkspace(): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (!ledgerUuid) return;
    this.loading.set(true);
    this.error.set(null);
    this.workspaceRequest?.unsubscribe();
    this.workspaceRequest = forkJoin({
      accounts: this.entitiesService.listAccounts(ledgerUuid),
      currencies: this.entitiesService.listCurrencies(ledgerUuid),
      categories: this.categoriesService.getTree(ledgerUuid),
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: ({ accounts, currencies, categories }) => {
        this.accounts.set(accounts);
        this.currencies.set(currencies);
        this.categoryTree.set(categories);
        this.loadEvents();
      },
      error: error => {
        this.loading.set(false);
        this.error.set(this.errors.message(error, 'errors.activityResourcesLoadFailed'));
      },
    });
  }

  private loadEvents(): void {
    const ledgerUuid = this.context.ledgerUuid();
    const query = this.filterQuery();
    if (!ledgerUuid || !query) {
      this.loading.set(false);
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.nextCursor.set(null);
    this.appliedFilters.set(query);
    this.loadAccountBalance(query);
    this.loadCashFlowSummary(query);
    this.eventsRequest?.unsubscribe();
    this.moreRequest?.unsubscribe();
    this.eventsRequest = this.eventsService.list(ledgerUuid, query).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loading.set(false)),
    ).subscribe({
      next: page => {
        this.events.set(page.events);
        this.nextCursor.set(page.next_cursor);
        this.totalEventCount.set(page.total_count);
      },
      error: error => this.error.set(this.errors.message(error, 'errors.financialEventsLoadFailed')),
    });
  }

  private loadAccountBalance(filters: Omit<FinancialEventFilters, 'cursor'>): void {
    const ledgerUuid = this.context.ledgerUuid();
    this.balanceRequest?.unsubscribe();
    this.accountBalance.set(null);
    this.balanceUnavailable.set(false);
    if (!ledgerUuid || !filters.account_uuid) {
      this.balanceLoading.set(false);
      return;
    }

    this.balanceLoading.set(true);
    this.balanceRequest = this.entitiesService.getAccountBalance(ledgerUuid, filters.account_uuid, filters.to_timestamp - 1).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.balanceLoading.set(false)),
    ).subscribe({
      next: balance => this.accountBalance.set(balance),
      error: () => this.balanceUnavailable.set(true),
    });
  }

  private loadCashFlowSummary(filters: Omit<FinancialEventFilters, 'cursor'>): void {
    const ledgerUuid = this.context.ledgerUuid();
    this.summaryRequest?.unsubscribe();
    this.cashFlowSummary.set(null);
    this.summaryUnavailable.set(false);
    const account = filters.account_uuid ? this.accountByUuid().get(filters.account_uuid) ?? null : null;
    const currency = account ? this.currencyByUuid().get(account.currency_uuid) ?? null : null;
    if (!ledgerUuid || !currency) {
      this.summaryLoading.set(false);
      return;
    }

    this.summaryLoading.set(true);
    this.summaryRequest = this.cashFlowService.summary(ledgerUuid, currency.uuid, filters).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.summaryLoading.set(false)),
    ).subscribe({
      next: summary => this.cashFlowSummary.set(summary),
      error: () => this.summaryUnavailable.set(true),
    });
  }

  private filterQuery(): Omit<FinancialEventFilters, 'cursor'> | null {
    const value = this.filters.getRawValue();
    const timezone = this.preferences.current().timezone;
    const from = zonedDateTimeToEpochSeconds(value.from_date, '00:00', timezone);
    const toExclusiveDate = this.nextDate(value.to_date);
    const to = toExclusiveDate ? zonedDateTimeToEpochSeconds(toExclusiveDate, '00:00', timezone) : null;
    if (from === null || to === null || from >= to) {
      this.filterError.set(this.i18n.t('activity.validation.period'));
      return null;
    }
    this.filterError.set(null);
    return {
      from_timestamp: from,
      to_timestamp: to,
      page_size: EVENT_BATCH_SIZE,
      account_uuid: value.account_uuid || null,
      category_uuid: value.category_uuid || null,
      description_search: value.description_search.trim() || null,
      ascending: false,
    };
  }

  private resetFilters(emitEvent = true): void {
    this.periodMode.set('month');
    this.selectedMonth.set(this.currentMonth());
    const dates = this.monthDates(this.selectedMonth());
    this.filters.reset({
      from_date: dates?.from ?? '',
      to_date: dates?.to ?? '',
      account_uuid: '',
      category_uuid: '',
      description_search: '',
    }, { emitEvent });
    this.filterError.set(null);
  }

  private restoreFilters(ledgerUuid: string | null): void {
    const saved = ledgerUuid ? this.workspaceState.getActivity(ledgerUuid) : null;
    if (saved) {
      this.filters.reset({ ...saved, description_search: saved.description_search ?? '' }, { emitEvent: false });
      const month = this.monthForRange(saved.from_date, saved.to_date);
      this.periodMode.set(month ? 'month' : 'range');
      this.selectedMonth.set(month ?? (saved.from_date.slice(0, 7) || this.currentMonth()));
      this.filterError.set(null);
      return;
    }
    this.resetFilters(false);
  }

  private saveFilters(): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (ledgerUuid) this.workspaceState.setActivity(ledgerUuid, this.filters.getRawValue());
  }

  private resetTransientState(): void {
    this.accounts.set([]);
    this.currencies.set([]);
    this.categoryTree.set([]);
    this.events.set([]);
    this.totalEventCount.set(0);
    this.nextCursor.set(null);
    this.appliedFilters.set(null);
    this.accountBalance.set(null);
    this.balanceLoading.set(false);
    this.balanceUnavailable.set(false);
    this.cashFlowSummary.set(null);
    this.summaryLoading.set(false);
    this.summaryUnavailable.set(false);
    this.createMenuOpen.set(false);
    this.editorType.set(null);
    this.editingEvent.set(null);
    this.deleting.set(null);
  }

  private flattenCategories(nodes: readonly LedgerCategoryTreeNode[]): LedgerCategory[] {
    return nodes.flatMap(node => [node.category, ...this.flattenCategories(node.children)]);
  }

  private aggregateMovements(event: FinancialEvent) {
    if (event.type !== 'ACCOUNT_TRANSFER') return event.movements;
    const destination = event.movements.find(movement => movement.value > 0) ?? null;
    const source = destination ? event.movements.find(movement => movement.value < 0 && movement.account_uuid !== destination.account_uuid) ?? null : null;
    return source && destination ? [source, destination] : event.movements;
  }

  private syncMonthToFilters(): void {
    const dates = this.monthDates(this.selectedMonth());
    if (!dates) return;
    this.filters.patchValue({ from_date: dates.from, to_date: dates.to });
  }

  private monthForRange(from: string, to: string): string | null {
    const month = from.slice(0, 7);
    const dates = this.monthDates(month);
    return dates?.from === from && dates.to === to ? month : null;
  }

  private monthDates(month: string): { from: string; to: string } | null {
    const match = /^(\d{4})-(\d{2})$/.exec(month);
    if (!match) return null;
    const year = Number(match[1]);
    const monthNumber = Number(match[2]);
    if (monthNumber < 1 || monthNumber > 12) return null;
    const lastDay = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
    const prefix = `${String(year).padStart(4, '0')}-${String(monthNumber).padStart(2, '0')}`;
    return { from: `${prefix}-01`, to: `${prefix}-${String(lastDay).padStart(2, '0')}` };
  }

  private currentMonth(): string {
    return zonedDateInput(Math.floor(Date.now() / 1000), this.preferences.current().timezone).slice(0, 7);
  }

  private nextDate(value: string): string | null {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!match) return null;
    const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]) + 1));
    if (Number.isNaN(date.getTime())) return null;
    return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`;
  }
}
