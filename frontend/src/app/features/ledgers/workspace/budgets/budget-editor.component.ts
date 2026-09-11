import { formatDate } from '@angular/common';
import { DialogShellComponent } from '../../../../shared/ui/dialog-shell.component';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, output, signal, untracked } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerBudget } from '../../../../core/ledgers/ledger-budgets.models';
import { LedgerBudgetsService } from '../../../../core/ledgers/ledger-budgets.service';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { categoryPath } from '../../../../core/ledgers/ledger-category-tree';
import { LedgerAccount, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { currencyAmountInput, parseCurrencyAmount } from '../../../../core/ledgers/currency-format';
import { CurrencyAmountInputComponent } from '../../../../shared/ledger/currency-amount-input.component';
import { EntitySearchOption, EntitySearchSelectComponent } from '../../../../shared/ledger/entity-search-select.component';
import { FieldErrorComponent } from '../../../../shared/ui/field-error.component';
import { FormMessageComponent } from '../../../../shared/ui/form-message.component';
import { IconComponent } from '../../../../shared/ui/icon.component';

@Component({
  selector: 'app-budget-editor',
  standalone: true,
  imports: [DialogShellComponent, ReactiveFormsModule, CurrencyAmountInputComponent, EntitySearchSelectComponent, FieldErrorComponent, FormMessageComponent, IconComponent],
  templateUrl: './budget-editor.component.html',
  styleUrl: './budget-editor.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BudgetEditorComponent {
  private readonly fb = inject(FormBuilder);
  private readonly budgets = inject(LedgerBudgetsService);
  private readonly errors = inject(ApiErrorService);
  private readonly destroyRef = inject(DestroyRef);
  readonly i18n = inject(I18nService);

  readonly ledgerUuid = input.required<string>();
  readonly budget = input<LedgerBudget | null>(null);
  readonly accounts = input.required<readonly LedgerAccount[]>();
  readonly currencies = input.required<readonly LedgerCurrency[]>();
  readonly categories = input.required<readonly LedgerCategory[]>();
  readonly close = output<void>();
  readonly saved = output<LedgerBudget>();
  readonly deleteRequested = output<LedgerBudget>();

  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(50), Validators.pattern(/\S/)]],
    description: ['', [Validators.maxLength(300)]],
    account_uuid: ['', Validators.required],
    category_uuid: ['', Validators.required],
    from_date: ['', Validators.required],
    to_date: ['', Validators.required],
    amount: ['', Validators.required],
  });
  readonly values = signal(this.form.getRawValue());
  readonly title = computed(() => this.i18n.t(this.budget() ? 'budgets.edit' : 'budgets.create'));
  readonly currencyByUuid = computed(() => new Map(this.currencies().map(currency => [currency.uuid, currency] as const)));
  readonly accountByUuid = computed(() => new Map(this.accounts().map(account => [account.uuid, account] as const)));
  readonly selectedAccount = computed(() => this.accountByUuid().get(this.values().account_uuid) ?? null);
  readonly selectedCurrency = computed(() => {
    const account = this.selectedAccount();
    return account ? this.currencyByUuid().get(account.currency_uuid) ?? null : null;
  });
  readonly accountOptions = computed<EntitySearchOption[]>(() => this.accounts().map(account => ({
    value: account.uuid,
    label: account.name,
    detail: this.currencyByUuid().get(account.currency_uuid)?.name ?? null,
    icon: account.icon,
    color: account.color_code,
  })));
  readonly categoryOptions = computed<EntitySearchOption[]>(() => {
    const byUuid = new Map(this.categories().map(category => [category.uuid, category] as const));
    return this.categories().map(category => ({
      value: category.uuid,
      label: category.name,
      detail: categoryPath(category, byUuid) || null,
      icon: category.icon,
      color: category.color_code,
    }));
  });

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.values.set(this.form.getRawValue()));
    let previousCurrencyUuid: string | null = null;
    this.form.controls.account_uuid.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(accountUuid => {
      const currencyUuid = this.accountByUuid().get(accountUuid)?.currency_uuid ?? null;
      if (previousCurrencyUuid !== null && currencyUuid !== previousCurrencyUuid) this.form.controls.amount.setValue('');
      previousCurrencyUuid = currencyUuid;
    });
    effect(() => {
      const budget = this.budget();
      untracked(() => {
        const currency = budget ? this.currencyForBudget(budget) : null;
        this.form.reset({
          name: budget?.name ?? '',
          description: budget?.description ?? '',
          account_uuid: budget?.account_uuid ?? '',
          category_uuid: budget?.category_uuid ?? '',
          from_date: budget ? formatDate(budget.from_timestamp * 1000, 'yyyy-MM-dd', 'en-US') : '',
          to_date: budget ? formatDate(Math.max(budget.from_timestamp, budget.to_timestamp - 1) * 1000, 'yyyy-MM-dd', 'en-US') : '',
          amount: budget && currency ? currencyAmountInput(budget.amount, currency.decimal_places) : '',
        });
        previousCurrencyUuid = budget ? this.accountByUuid().get(budget.account_uuid)?.currency_uuid ?? null : null;
        this.error.set(null);
      });
    });
  }

  requestClose(): void { if (!this.saving()) this.close.emit(); }

  setAccount(value: string): void {
    if (this.budget()) return;
    this.form.controls.account_uuid.setValue(value);
    this.form.controls.account_uuid.markAsDirty();
  }

  setCategory(value: string): void {
    this.form.controls.category_uuid.setValue(value);
    this.form.controls.category_uuid.markAsDirty();
  }

  setAmount(value: string): void {
    this.form.controls.amount.setValue(value);
    this.form.controls.amount.markAsDirty();
  }

  fieldError(name: keyof typeof this.form.controls): string | null {
    const control = this.form.controls[name];
    if (!(control.dirty || control.touched) || control.valid) return null;
    if (control.hasError('maxlength')) return this.i18n.t('validation.ledgerNameMax', { max: control.getError('maxlength').requiredLength });
    return this.i18n.t('validation.required');
  }

  save(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid || this.saving()) return;
    const value = this.form.getRawValue();
    const currency = this.selectedCurrency();
    const fromDate = new Date(`${value.from_date}T00:00:00`);
    const toDate = new Date(`${value.to_date}T00:00:00`);
    const validDates = !Number.isNaN(fromDate.getTime()) && !Number.isNaN(toDate.getTime())
      && formatDate(fromDate, 'yyyy-MM-dd', 'en-US') === value.from_date
      && formatDate(toDate, 'yyyy-MM-dd', 'en-US') === value.to_date;
    toDate.setDate(toDate.getDate() + 1);
    const fromTimestamp = Math.floor(fromDate.getTime() / 1000);
    const toTimestamp = Math.floor(toDate.getTime() / 1000);
    const amount = currency ? parseCurrencyAmount(value.amount, currency.decimal_places) : null;
    if (!validDates || fromTimestamp >= toTimestamp) {
      this.error.set(this.i18n.t('budgets.validation.period'));
      return;
    }
    if (amount === null || amount < 0) {
      this.error.set(this.i18n.t('budgets.validation.amount'));
      return;
    }

    const common = {
      category_uuid: value.category_uuid,
      from_timestamp: fromTimestamp,
      to_timestamp: toTimestamp,
      name: value.name.trim(),
      description: value.description.trim() || null,
      amount,
    };
    const current = this.budget();
    const request = current
      ? this.budgets.update(this.ledgerUuid(), current.uuid, common)
      : this.budgets.create(this.ledgerUuid(), { ...common, account_uuid: value.account_uuid });
    this.saving.set(true);
    this.error.set(null);
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving.set(false))).subscribe({
      next: budget => this.saved.emit(budget),
      error: error => this.error.set(this.errors.message(error, 'errors.budgetSaveFailed')),
    });
  }

  private currencyForBudget(budget: LedgerBudget): LedgerCurrency | null {
    const account = this.accountByUuid().get(budget.account_uuid);
    return account ? this.currencyByUuid().get(account.currency_uuid) ?? null : null;
  }

}
