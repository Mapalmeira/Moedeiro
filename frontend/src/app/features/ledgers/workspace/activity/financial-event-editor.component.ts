import { formatDate } from '@angular/common';
import { DialogShellComponent } from '../../../../shared/ui/dialog-shell.component';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, output, signal, untracked } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ReactiveFormsModule, Validators } from '@angular/forms';
import { FormBuilder } from '@angular/forms';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { categoryPath } from '../../../../core/ledgers/ledger-category-tree';
import { currencyAmountInput, parseCurrencyAmount } from '../../../../core/ledgers/currency-format';
import { LedgerAccount, LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import {
  AccountTransferFinancialEventPayload,
  CreateFinancialEventPayload,
  FinancialEvent,
  FinancialEventType,
  MAX_SHOPPING_LIST_MOVEMENTS,
  ShoppingListFinancialEventPayload,
  SimpleFinancialEventPayload,
  UpdateFinancialEventPayload,
} from '../../../../core/ledgers/financial-events.models';
import { FinancialEventsService } from '../../../../core/ledgers/financial-events.service';
import { financialEventFeeMovement, financialEventMainMovements } from '../../../../core/ledgers/financial-event-movements';
import { CurrencyAmountInputComponent } from '../../../../shared/ledger/currency-amount-input.component';
import { EntitySearchOption, EntitySearchSelectComponent } from '../../../../shared/ledger/entity-search-select.component';
import { FieldErrorComponent } from '../../../../shared/ui/field-error.component';
import { FormMessageComponent } from '../../../../shared/ui/form-message.component';
import { IconComponent, IconName } from '../../../../shared/ui/icon.component';
import { financialEventPresentation } from '../../../../shared/ledger/financial-event-presentation';

@Component({
  selector: 'app-financial-event-editor',
  standalone: true,
  imports: [DialogShellComponent, ReactiveFormsModule, CurrencyAmountInputComponent, EntitySearchSelectComponent, FieldErrorComponent, FormMessageComponent, IconComponent],
  templateUrl: './financial-event-editor.component.html',
  styleUrl: './financial-event-editor.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FinancialEventEditorComponent {
  private readonly fb = inject(FormBuilder);
  private readonly eventsService = inject(FinancialEventsService);
  private readonly errors = inject(ApiErrorService);
  private readonly destroyRef = inject(DestroyRef);
  readonly i18n = inject(I18nService);
  readonly maxShoppingMovements = MAX_SHOPPING_LIST_MOVEMENTS;

  readonly ledgerUuid = input.required<string>();
  readonly type = input.required<FinancialEventType>();
  readonly event = input<FinancialEvent | null>(null);
  readonly accounts = input.required<readonly LedgerAccount[]>();
  readonly currencies = input.required<readonly LedgerCurrency[]>();
  readonly categories = input.required<readonly LedgerCategory[]>();
  readonly close = output<void>();
  readonly saved = output<FinancialEvent>();
  readonly deleteRequested = output<FinancialEvent>();

  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly invalidMovementIndexes = signal<readonly number[]>([]);
  readonly values = signal({
    source_account_uuid: '', destination_account_uuid: '', fee_enabled: false,
  });

  readonly form = this.fb.nonNullable.group({
    description: ['', [Validators.required, Validators.maxLength(300), Validators.pattern(/\S/)]],
    date: ['', Validators.required],
    time: ['', Validators.required],
    account_uuid: ['', Validators.required],
    category_uuid: ['', Validators.required],
    amount: ['', Validators.required],
    direction: ['EXPENSE' as 'EXPENSE' | 'INCOME', Validators.required],
    source_account_uuid: ['', Validators.required],
    destination_account_uuid: ['', Validators.required],
    source_amount: ['', Validators.required],
    destination_amount: [''],
    fee_enabled: [false],
    fee_amount: [''],
    fee_category_uuid: [''],
    movements: this.fb.array([] as ReturnType<typeof this.createMovementGroup>[]),
  });

  readonly movements = this.form.controls.movements;
  readonly title = computed(() => this.i18n.t(this.event() ? 'activity.editor.edit' : this.titleKey(this.type())));
  readonly titlePresentation = computed(() => financialEventPresentation(this.type()));
  readonly titleIcon = computed<IconName>(() => this.titlePresentation().icon);
  readonly sameTransferCurrency = computed(() => {
    const values = this.values();
    const source = this.accountCurrency(values.source_account_uuid);
    const destination = this.accountCurrency(values.destination_account_uuid);
    return !!source && !!destination && source.uuid === destination.uuid;
  });
  private readonly accountByUuid = computed(() => new Map(this.accounts().map(account => [account.uuid, account] as const)));
  private readonly currencyByUuid = computed(() => new Map(this.currencies().map(currency => [currency.uuid, currency] as const)));
  readonly accountOptions = computed<readonly EntitySearchOption[]>(() => this.accounts().map(account => ({
    value: account.uuid,
    label: account.name,
    detail: this.accountCurrencyName(account.uuid),
    icon: account.icon,
    color: account.color_code,
  })));
  readonly categoryOptions = computed<readonly EntitySearchOption[]>(() => {
    const byUuid = new Map(this.categories().map(category => [category.uuid, category] as const));
    return this.categories().map(category => {
      const path = categoryPath(category, byUuid);
      return {
        value: category.uuid,
        label: category.name,
        detail: path === category.name ? null : path,
        icon: category.icon,
        color: category.color_code,
      };
    });
  });

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(value => {
      this.values.set({
        source_account_uuid: value.source_account_uuid ?? '',
        destination_account_uuid: value.destination_account_uuid ?? '',
        fee_enabled: value.fee_enabled ?? false,
      });
      this.error.set(null);
      this.invalidMovementIndexes.set([]);
    });
    effect(() => {
      const event = this.event();
      const type = this.type();
      untracked(() => this.reset(event, type));
    });
  }

  requestClose(): void {
    if (!this.saving()) this.close.emit();
  }

  addMovement(): void {
    if (this.movements.length >= this.maxShoppingMovements) return;
    this.movements.push(this.createMovementGroup());
  }

  removeMovement(index: number): void {
    if (this.movements.length <= 1) return;
    this.movements.removeAt(index);
  }

  toggleFee(): void {
    const control = this.form.controls.fee_enabled;
    control.setValue(!control.value);
    control.markAsDirty();
  }

  accountCurrency(accountUuid: string): LedgerCurrency | null {
    const currencyUuid = this.accountByUuid().get(accountUuid)?.currency_uuid;
    return currencyUuid ? this.currencyByUuid().get(currencyUuid) ?? null : null;
  }

  accountCurrencyName(accountUuid: string): string {
    return this.accountCurrency(accountUuid)?.name ?? '';
  }

  setControlValue(name: 'account_uuid' | 'category_uuid' | 'source_account_uuid' | 'destination_account_uuid' | 'fee_category_uuid', value: string): void {
    this.form.controls[name].setValue(value);
    this.form.controls[name].markAsDirty();
  }

  setMovementCategory(index: number, value: string): void {
    const control = this.movements.at(index).controls.category_uuid;
    control.setValue(value);
    control.markAsDirty();
  }

  setMovementAmount(index: number, value: string): void {
    const control = this.movements.at(index).controls.amount;
    control.setValue(value);
    control.markAsDirty();
  }

  setAmountControl(name: 'amount' | 'source_amount' | 'destination_amount' | 'fee_amount', value: string): void {
    this.form.controls[name].setValue(value);
    this.form.controls[name].markAsDirty();
  }

  fieldError(name: keyof typeof this.form.controls): string | null {
    const control = this.form.controls[name];
    if (!(control.dirty || control.touched) || control.valid) return null;
    if (control.hasError('required')) return this.i18n.t('validation.required');
    if (control.hasError('maxlength')) return this.i18n.t('activity.validation.descriptionMax');
    return this.i18n.t('validation.required');
  }

  save(): void {
    this.form.markAllAsTouched();
    this.movements.controls.forEach(control => control.markAllAsTouched());
    if (this.saving() || this.form.controls.description.invalid || this.form.controls.date.invalid || this.form.controls.time.invalid) return;

    const value = this.form.getRawValue();
    const occurredAtMs = Date.parse(`${value.date}T${value.time}`);
    if (Number.isNaN(occurredAtMs) || formatDate(occurredAtMs, 'yyyy-MM-dd', 'en-US') !== value.date) {
      this.error.set(this.i18n.t('activity.validation.dateTime'));
      return;
    }

    const payload = this.buildPayload(Math.floor(occurredAtMs / 1000));
    if (!payload) return;
    this.saving.set(true);
    this.error.set(null);
    const current = this.event();
    const request = current
      ? this.eventsService.update(this.ledgerUuid(), current.uuid, payload as UpdateFinancialEventPayload)
      : this.eventsService.create(this.ledgerUuid(), payload as CreateFinancialEventPayload);
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving.set(false))).subscribe({
      next: saved => this.saved.emit(saved),
      error: error => this.error.set(this.errors.message(error, 'errors.financialEventSaveFailed')),
    });
  }

  private buildPayload(occurredAt: number): UpdateFinancialEventPayload | CreateFinancialEventPayload | null {
    const value = this.form.getRawValue();
    const description = value.description.trim();
    if (this.type() === 'TRANSACTION') {
      const currency = this.accountCurrency(value.account_uuid);
      const amount = currency ? parseCurrencyAmount(value.amount, currency.decimal_places) : null;
      if (!value.account_uuid || !value.category_uuid || !currency || !amount) return this.invalidAmount();
      let fee: SimpleFinancialEventPayload['fee'] = null;
      if (value.direction === 'EXPENSE' && value.fee_enabled) {
        const feeAmount = parseCurrencyAmount(value.fee_amount, currency.decimal_places);
        if (!value.fee_category_uuid || !feeAmount) return this.invalidAmount();
        fee = { category_uuid: value.fee_category_uuid, value: -feeAmount };
      }
      const payload: SimpleFinancialEventPayload = {
        type: 'TRANSACTION', occurred_at: occurredAt, description,
        account_uuid: value.account_uuid, category_uuid: value.category_uuid,
        value: value.direction === 'EXPENSE' ? -amount : amount, quantity: 1, item_name: null, fee,
      };
      return payload;
    }

    if (this.type() === 'SHOPPING_LIST') {
      const currency = this.accountCurrency(value.account_uuid);
      if (!value.account_uuid || !currency || this.movements.length === 0) {
        this.invalidMovementIndexes.set(this.movements.controls.map((_, index) => index));
        return null;
      }
      const invalidIndexes: number[] = [];
      const movements = this.movements.getRawValue().map((movement, index) => {
        const amount = parseCurrencyAmount(movement.amount, currency.decimal_places);
        const quantity = Number(movement.quantity);
        const itemName = movement.item_name.trim();
        const valid = !!amount && !!movement.category_uuid && Number.isInteger(quantity) && quantity > 0 && itemName.length <= 50;
        if (!valid) {
          invalidIndexes.push(index);
          return null;
        }
        return {
          uuid: movement.uuid || null,
          category_uuid: movement.category_uuid,
          value: -amount,
          quantity,
          item_name: itemName || null,
        };
      });
      if (invalidIndexes.length) {
        this.invalidMovementIndexes.set(invalidIndexes);
        return null;
      }
      const normalizedMovements = movements as ShoppingListFinancialEventPayload['movements'];
      if (!this.event()) {
        return {
          type: 'SHOPPING_LIST', occurred_at: occurredAt, description, account_uuid: value.account_uuid,
          movements: normalizedMovements.map(({ category_uuid, value: movementValue, quantity, item_name }) => ({
            category_uuid, value: movementValue, quantity, item_name,
          })),
        };
      }
      const payload: ShoppingListFinancialEventPayload = {
        type: 'SHOPPING_LIST', occurred_at: occurredAt, description, account_uuid: value.account_uuid,
        movements: normalizedMovements,
      };
      return payload;
    }

    const sourceCurrency = this.accountCurrency(value.source_account_uuid);
    const destinationCurrency = this.accountCurrency(value.destination_account_uuid);
    const sourceAmount = sourceCurrency ? parseCurrencyAmount(value.source_amount, sourceCurrency.decimal_places) : null;
    if (!value.source_account_uuid || !value.destination_account_uuid || value.source_account_uuid === value.destination_account_uuid ||
        !value.category_uuid || !sourceCurrency || !destinationCurrency || !sourceAmount) {
      this.error.set(value.source_account_uuid === value.destination_account_uuid
        ? this.i18n.t('activity.validation.transferAccounts')
        : this.i18n.t('activity.validation.amount'));
      return null;
    }
    const destinationAmount = sourceCurrency.uuid === destinationCurrency.uuid
      ? sourceAmount
      : parseCurrencyAmount(value.destination_amount, destinationCurrency.decimal_places);
    if (!destinationAmount) return this.invalidAmount();

    let fee: AccountTransferFinancialEventPayload['fee'] = null;
    if (value.fee_enabled) {
      const feeAmount = parseCurrencyAmount(value.fee_amount, destinationCurrency.decimal_places);
      if (!value.fee_category_uuid || !feeAmount) return this.invalidAmount();
      fee = { category_uuid: value.fee_category_uuid, value: -feeAmount };
    }
    return {
      type: 'ACCOUNT_TRANSFER', occurred_at: occurredAt, description,
      source_account_uuid: value.source_account_uuid,
      source_category_uuid: value.category_uuid,
      source_value: -sourceAmount,
      destination_account_uuid: value.destination_account_uuid,
      destination_category_uuid: value.category_uuid,
      destination_value: destinationAmount,
      fee,
    };
  }

  private invalidAmount(): null {
    this.error.set(this.i18n.t('activity.validation.amount'));
    return null;
  }

  private reset(event: FinancialEvent | null, type: FinancialEventType): void {
    const timestamp = event?.occurred_at ?? Math.floor(Date.now() / 1000);
    const firstAccount = this.accounts()[0]?.uuid ?? '';
    const secondAccount = this.accounts().find(account => account.uuid !== firstAccount)?.uuid ?? '';
    const firstCategory = this.categories()[0]?.uuid ?? '';
    this.movements.clear();

    this.form.reset({
      description: event?.description ?? '',
      date: formatDate(timestamp * 1000, 'yyyy-MM-dd', 'en-US'),
      time: formatDate(timestamp * 1000, 'HH:mm:ss', 'en-US'),
      account_uuid: firstAccount,
      category_uuid: firstCategory,
      amount: '', direction: 'EXPENSE',
      source_account_uuid: firstAccount,
      destination_account_uuid: secondAccount,
      source_amount: '', destination_amount: '',
      fee_enabled: false, fee_amount: '', fee_category_uuid: firstCategory,
    });

    if (!event) {
      if (type === 'SHOPPING_LIST') this.addMovement();
      this.values.set({ source_account_uuid: firstAccount, destination_account_uuid: secondAccount, fee_enabled: false });
      this.error.set(null);
      return;
    }

    if (type === 'TRANSACTION') {
      const movement = financialEventMainMovements(event)[0];
      const fee = financialEventFeeMovement(event);
      if (movement) {
        const currency = this.accountCurrency(movement.account_uuid);
        this.form.patchValue({
          account_uuid: movement.account_uuid,
          category_uuid: movement.category_uuid,
          amount: currency ? currencyAmountInput(movement.value, currency.decimal_places) : '',
          direction: movement.value < 0 ? 'EXPENSE' : 'INCOME',
          fee_enabled: !!fee,
          fee_amount: fee && currency ? currencyAmountInput(fee.value, currency.decimal_places) : '',
          fee_category_uuid: fee?.category_uuid ?? firstCategory,
        });
      }
    } else if (type === 'SHOPPING_LIST') {
      const accountUuid = event.movements[0]?.account_uuid ?? firstAccount;
      const currency = this.accountCurrency(accountUuid);
      this.form.controls.account_uuid.setValue(accountUuid);
      for (const movement of event.movements) {
        this.movements.push(this.createMovementGroup({
          uuid: movement.uuid,
          category_uuid: movement.category_uuid,
          amount: currency ? currencyAmountInput(movement.value, currency.decimal_places) : '',
          item_name: movement.item_name ?? '',
          quantity: movement.quantity,
        }));
      }
      if (this.movements.length === 0) this.addMovement();
    } else {
      const mainMovements = financialEventMainMovements(event);
      const destination = mainMovements.find(movement => movement.value > 0) ?? null;
      const source = destination ? mainMovements.find(movement => movement.value < 0 && movement.account_uuid !== destination.account_uuid) ?? null : null;
      const fee = financialEventFeeMovement(event);
      if (source && destination) {
        const sourceCurrency = this.accountCurrency(source.account_uuid);
        const destinationCurrency = this.accountCurrency(destination.account_uuid);
        this.form.patchValue({
          source_account_uuid: source.account_uuid,
          destination_account_uuid: destination.account_uuid,
          category_uuid: source.category_uuid,
          source_amount: sourceCurrency ? currencyAmountInput(source.value, sourceCurrency.decimal_places) : '',
          destination_amount: destinationCurrency ? currencyAmountInput(destination.value, destinationCurrency.decimal_places) : '',
          fee_enabled: !!fee,
          fee_amount: fee && destinationCurrency ? currencyAmountInput(fee.value, destinationCurrency.decimal_places) : '',
          fee_category_uuid: fee?.category_uuid ?? firstCategory,
        });
      }
    }
    this.values.set({
      source_account_uuid: this.form.controls.source_account_uuid.value,
      destination_account_uuid: this.form.controls.destination_account_uuid.value,
      fee_enabled: this.form.controls.fee_enabled.value,
    });
    this.error.set(null);
    this.invalidMovementIndexes.set([]);
  }

  private createMovementGroup(initial?: { uuid?: string; category_uuid?: string; amount?: string; item_name?: string; quantity?: number }) {
    return this.fb.nonNullable.group({
      uuid: [initial?.uuid ?? ''],
      category_uuid: [initial?.category_uuid ?? this.categories()[0]?.uuid ?? '', Validators.required],
      item_name: [initial?.item_name ?? '', Validators.maxLength(50)],
      quantity: [initial?.quantity ?? 1, [Validators.required, Validators.min(1), Validators.pattern(/^\d+$/)]],
      amount: [initial?.amount ?? '', Validators.required],
    });
  }

  private titleKey(type: FinancialEventType): 'activity.editor.createSimple' | 'activity.editor.createShopping' | 'activity.editor.createTransfer' {
    if (type === 'SHOPPING_LIST') return 'activity.editor.createShopping';
    if (type === 'ACCOUNT_TRANSFER') return 'activity.editor.createTransfer';
    return 'activity.editor.createSimple';
  }
}
