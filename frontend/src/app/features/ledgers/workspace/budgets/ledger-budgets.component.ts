import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal, untracked } from '@angular/core';
import { DialogShellComponent } from '../../../../shared/ui/dialog-shell.component';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subject, Subscription, finalize, forkJoin, debounceTime, distinctUntilChanged } from 'rxjs';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { categoryPath, flattenCategoryTree } from '../../../../core/ledgers/ledger-category-tree';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { LedgerBudget, LedgerBudgetOverview, LedgerBudgetState } from '../../../../core/ledgers/ledger-budgets.models';
import { LedgerBudgetsService } from '../../../../core/ledgers/ledger-budgets.service';
import { LedgerAccount, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../../core/ledgers/ledger-entities.service';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { LedgerWorkspaceStateService } from '../../../../core/ledgers/ledger-workspace-state.service';
import { formatCurrencyAmount } from '../../../../core/ledgers/currency-format';
import { EntityBadgeComponent } from '../../../../shared/ledger/entity-badge.component';
import { EntitySearchOption, EntitySearchSelectComponent } from '../../../../shared/ledger/entity-search-select.component';
import { FormMessageComponent } from '../../../../shared/ui/form-message.component';
import { IconComponent, IconName } from '../../../../shared/ui/icon.component';
import { InfiniteScrollTriggerDirective } from '../../../../shared/ui/infinite-scroll-trigger.directive';
import { BudgetEditorComponent } from './budget-editor.component';
import { BudgetStateFilterComponent } from './budget-state-filter.component';

interface BudgetCardView {
  budget: LedgerBudgetOverview;
  account: LedgerAccount | null;
  category: LedgerCategory | null;
  currency: LedgerCurrency | null;
  categoryPath: string;
  period: string;
  stateLabel: string;
  stateIcon: IconName;
  stateDetail: string;
  amountLabel: string;
  spentLabel: string | null;
  summaryLabel: string | null;
  usageLabel: string | null;
  progress: number;
  tone: 'green' | 'yellow' | 'danger' | 'neutral';
}

const PAGE_SIZE = 30;
const WARNING_USAGE_PERCENT = 80;
const ALL_STATES: readonly LedgerBudgetState[] = ['ACTIVE', 'FUTURE', 'FINISHED'];

@Component({
  selector: 'app-ledger-budgets',
  standalone: true,
  imports: [DialogShellComponent, 
    BudgetEditorComponent,
    BudgetStateFilterComponent,
    EntityBadgeComponent,
    EntitySearchSelectComponent,
    FormMessageComponent,
    IconComponent,
    InfiniteScrollTriggerDirective,
  ],
  templateUrl: './ledger-budgets.component.html',
  styleUrl: './ledger-budgets.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerBudgetsComponent {
  private readonly budgets = inject(LedgerBudgetsService);
  private readonly entities = inject(LedgerEntitiesService);
  private readonly categoriesService = inject(LedgerCategoriesService);
  private readonly errors = inject(ApiErrorService);
  private readonly workspaceState = inject(LedgerWorkspaceStateService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly searchChanges = new Subject<string>();
  private overviewRequest?: Subscription;
  private resourcesRequest?: Subscription;
  readonly context = inject(LedgerContextService);
  readonly i18n = inject(I18nService);

  readonly accounts = signal<LedgerAccount[]>([]);
  readonly currencies = signal<LedgerCurrency[]>([]);
  readonly categories = signal<LedgerCategory[]>([]);
  readonly items = signal<LedgerBudgetOverview[]>([]);
  readonly states = signal<readonly LedgerBudgetState[]>(ALL_STATES);
  readonly categoryFilterUuid = signal('');
  readonly search = signal('');
  readonly resourcesLoading = signal(false);
  readonly loading = signal(false);
  readonly loadingMore = signal(false);
  readonly error = signal<string | null>(null);
  readonly nextCursor = signal<string | null>(null);
  readonly editorOpen = signal(false);
  readonly editing = signal<LedgerBudget | null>(null);
  readonly deleting = signal<LedgerBudget | null>(null);
  readonly deletingBusy = signal(false);
  readonly deleteError = signal<string | null>(null);

  readonly accountByUuid = computed(() => new Map(this.accounts().map(account => [account.uuid, account] as const)));
  readonly currencyByUuid = computed(() => new Map(this.currencies().map(currency => [currency.uuid, currency] as const)));
  readonly categoryByUuid = computed(() => new Map(this.categories().map(category => [category.uuid, category] as const)));
  readonly categoryFilterOptions = computed<readonly EntitySearchOption[]>(() => {
    const byUuid = this.categoryByUuid();
    return [
      { value: '', label: this.i18n.t('categories.root'), uiIcon: 'LucideFolder', tone: 'neutral' },
      ...this.categories().map(category => {
        const path = categoryPath(category, byUuid);
        return {
          value: category.uuid,
          label: category.name,
          detail: path === category.name ? null : path,
          icon: category.icon,
          color: category.color_code,
        };
      }),
    ];
  });
  readonly canCreate = computed(() => this.accounts().length > 0 && this.categories().length > 0 && !this.resourcesLoading() && !this.error());
  readonly percentFormatter = new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 1 });
  readonly dateFormatter = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: '2-digit', day: '2-digit' });
  readonly cards = computed<BudgetCardView[]>(() => {
    const accountByUuid = this.accountByUuid();
    const currencyByUuid = this.currencyByUuid();
    const categoryByUuid = this.categoryByUuid();
    this.i18n.language();
    return this.items().map(budget => {
      const account = accountByUuid.get(budget.account_uuid) ?? null;
      const currency = account ? currencyByUuid.get(account.currency_uuid) ?? null : null;
      const category = categoryByUuid.get(budget.category_uuid) ?? null;
      const from = this.dateFormatter.format(new Date(budget.from_timestamp * 1000));
      const to = this.dateFormatter.format(new Date(Math.max(budget.from_timestamp, budget.to_timestamp - 1) * 1000));
      const spent = budget.spent_amount;
      const amountLabel = currency ? formatCurrencyAmount(budget.amount, currency) : String(budget.amount);
      const spentLabel = spent === null ? null : currency ? formatCurrencyAmount(spent, currency) : String(spent);
      const usage = spent === null ? null : this.usagePercent(spent, budget.amount);
      let stateLabel: string;
      let stateIcon: IconName;
      let stateDetail: string;
      let summaryLabel: string | null = null;
      let usageLabel: string | null = null;
      let tone: BudgetCardView['tone'] = 'neutral';
      let progress = 0;

      if (budget.state === 'FUTURE') {
        stateLabel = this.i18n.t('budgets.future');
        stateIcon = 'LucideCalendarDays';
        stateDetail = this.i18n.t('budgets.startsOn', { date: from });
      } else if (budget.state === 'ACTIVE') {
        stateLabel = this.i18n.t('budgets.active');
        stateIcon = 'LucideClock';
        stateDetail = this.i18n.t('budgets.endsOn', { date: to });
        usageLabel = usage === null ? null : this.i18n.t('budgets.usedPercent', { percent: this.formatPercent(usage) });
        progress = Number.isFinite(usage ?? 0) ? Math.min(100, Math.max(0, usage ?? 0)) : 100;
        if ((spent ?? 0) > budget.amount) {
          tone = 'danger';
          summaryLabel = this.i18n.t('budgets.overBy', { value: this.formatAmount((spent ?? 0) - budget.amount, currency) });
        } else {
          tone = (usage ?? 0) >= WARNING_USAGE_PERCENT ? 'yellow' : 'green';
          summaryLabel = this.i18n.t('budgets.available', { value: this.formatAmount(budget.amount - (spent ?? 0), currency) });
        }
      } else {
        stateLabel = budget.fulfilled ? this.i18n.t('budgets.fulfilled') : this.i18n.t('budgets.notFulfilled');
        stateIcon = budget.fulfilled ? 'LucideCheck' : 'LucideX';
        stateDetail = this.i18n.t('budgets.finishedOn', { date: to });
        usageLabel = usage === null ? null : this.i18n.t('budgets.usedPercent', { percent: this.formatPercent(usage) });
        progress = Number.isFinite(usage ?? 0) ? Math.min(100, Math.max(0, usage ?? 0)) : 100;
        tone = budget.fulfilled ? 'green' : 'danger';
        const difference = this.differencePercent(spent ?? 0, budget.amount);
        if (difference === null || difference === 0) {
          summaryLabel = budget.fulfilled ? this.i18n.t('budgets.atLimit') : this.i18n.t('budgets.overLimit');
        } else {
          summaryLabel = budget.fulfilled
            ? this.i18n.t('budgets.belowLimitPercent', { percent: this.formatPercent(difference) })
            : this.i18n.t('budgets.aboveLimitPercent', { percent: this.formatPercent(difference) });
        }
      }

      return {
        budget,
        account,
        category,
        currency,
        categoryPath: category ? categoryPath(category, categoryByUuid) : this.i18n.t('budgets.unknownCategory'),
        period: `${from} – ${to}`,
        stateLabel,
        stateIcon,
        stateDetail,
        amountLabel,
        spentLabel,
        summaryLabel,
        usageLabel,
        progress,
        tone,
      };
    });
  });

  constructor() {
    this.searchChanges.pipe(debounceTime(200), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef)).subscribe(value => {
      this.search.set(value);
      this.saveViewState();
      this.load(true);
    });
    effect(() => {
      const ledgerUuid = this.context.ledgerUuid();
      untracked(() => {
        this.closeEditor();
        this.restoreViewState(ledgerUuid);
        this.items.set([]);
        this.nextCursor.set(null);
        if (ledgerUuid) this.loadWorkspace();
      });
    });
  }

  updateSearch(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.saveViewState(value);
    this.searchChanges.next(value);
  }

  updateStates(states: readonly LedgerBudgetState[]): void {
    this.states.set(states);
    this.saveViewState();
    this.load(true);
  }

  updateCategoryFilter(categoryUuid: string): void {
    if (categoryUuid === this.categoryFilterUuid()) return;
    this.categoryFilterUuid.set(categoryUuid);
    this.saveViewState();
    this.load(true);
  }

  loadWorkspace(): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (!ledgerUuid) return;
    this.resourcesRequest?.unsubscribe();
    this.resourcesLoading.set(true);
    this.error.set(null);
    this.resourcesRequest = forkJoin({
      accounts: this.entities.listAccounts(ledgerUuid),
      currencies: this.entities.listCurrencies(ledgerUuid),
      tree: this.categoriesService.getTree(ledgerUuid),
    }).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.resourcesLoading.set(false))).subscribe({
      next: ({ accounts, currencies, tree }) => {
        this.accounts.set(accounts);
        this.currencies.set(currencies);
        const categories = flattenCategoryTree(tree);
        this.categories.set(categories);
        if (this.categoryFilterUuid() && !categories.some(category => category.uuid === this.categoryFilterUuid())) this.categoryFilterUuid.set('');
        this.saveViewState();
        this.resourcesLoading.set(false);
        this.load(true);
      },
      error: error => this.error.set(this.errors.message(error, 'errors.budgetResourcesLoadFailed')),
    });
  }

  load(reset: boolean): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (!ledgerUuid || this.resourcesLoading()) return;
    if (reset) {
      this.overviewRequest?.unsubscribe();
      this.loading.set(true);
      this.items.set([]);
      this.nextCursor.set(null);
    } else {
      if (this.loadingMore() || !this.nextCursor()) return;
      this.loadingMore.set(true);
    }
    this.error.set(null);
    this.overviewRequest = this.budgets.overview(ledgerUuid, {
      states: this.states(),
      pageSize: PAGE_SIZE,
      search: this.search(),
      categoryUuid: this.categoryFilterUuid() || null,
      cursor: reset ? null : this.nextCursor(),
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => reset ? this.loading.set(false) : this.loadingMore.set(false)),
    ).subscribe({
      next: page => {
        this.items.update(current => reset ? page.items : [...current, ...page.items]);
        this.nextCursor.set(page.next_cursor);
      },
      error: error => this.error.set(this.errors.message(error, 'errors.budgetsLoadFailed')),
    });
  }

  openCreate(): void {
    if (!this.canCreate()) return;
    this.editing.set(null);
    this.editorOpen.set(true);
  }

  openEdit(budget: LedgerBudget): void {
    this.editing.set(budget);
    this.editorOpen.set(true);
  }

  closeEditor(): void {
    this.editorOpen.set(false);
    this.editing.set(null);
  }

  saved(): void {
    this.closeEditor();
    this.load(true);
  }

  requestDelete(budget: LedgerBudget): void {
    this.deleteError.set(null);
    this.deleting.set(budget);
  }

  closeDelete(): void {
    if (!this.deletingBusy()) this.deleting.set(null);
  }

  remove(): void {
    const budget = this.deleting();
    const ledgerUuid = this.context.ledgerUuid();
    if (!budget || !ledgerUuid || this.deletingBusy()) return;
    this.deletingBusy.set(true);
    this.deleteError.set(null);
    this.budgets.delete(ledgerUuid, budget.uuid).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.deletingBusy.set(false)),
    ).subscribe({
      next: () => {
        this.deleting.set(null);
        this.closeEditor();
        this.load(true);
      },
      error: error => this.deleteError.set(this.errors.message(error, 'errors.budgetDeleteFailed')),
    });
  }


  private restoreViewState(ledgerUuid: string | null): void {
    const saved = ledgerUuid ? this.workspaceState.getBudgets(ledgerUuid) : null;
    this.states.set(saved?.states ?? ALL_STATES);
    this.categoryFilterUuid.set(saved?.category_uuid ?? '');
    this.search.set(saved?.search ?? '');
  }

  private saveViewState(search = this.search()): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (!ledgerUuid) return;
    this.workspaceState.setBudgets(ledgerUuid, {
      states: this.states(),
      category_uuid: this.categoryFilterUuid(),
      search,
    });
  }


  private usagePercent(spent: number, amount: number): number {
    if (amount === 0) return spent > 0 ? Number.POSITIVE_INFINITY : 0;
    return (spent / amount) * 100;
  }

  private differencePercent(spent: number, amount: number): number | null {
    if (amount === 0) return null;
    return Math.abs(spent - amount) / amount * 100;
  }

  private formatPercent(value: number): string {
    if (!Number.isFinite(value)) return '∞';
    return this.percentFormatter.format(value / 100);
  }

  private formatAmount(value: number, currency: LedgerCurrency | null): string {
    return currency ? formatCurrencyAmount(value, currency) : String(value);
  }
}
