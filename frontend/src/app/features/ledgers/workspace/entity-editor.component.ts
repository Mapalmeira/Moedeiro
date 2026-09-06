import { ChangeDetectionStrategy, Component, DestroyRef, HostListener, computed, effect, inject, input, output, signal, untracked } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable, finalize } from 'rxjs';
import { ApiErrorService } from '../../../core/api/api-error';
import { I18nService } from '../../../core/i18n/i18n.service';
import { LedgerAccount, LedgerCurrency } from '../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../core/ledgers/ledger-entities.service';
import { formatCurrencyPreview } from '../../../core/ledgers/currency-format';
import { PreferencesService } from '../../../core/preferences/preferences.service';
import { EntityBadgeComponent } from '../../../shared/ledger/entity-badge.component';
import { LedgerAppearanceFieldsComponent } from '../../../shared/ledger/ledger-appearance-fields.component';
import { FieldErrorComponent } from '../../../shared/ui/field-error.component';
import { FormMessageComponent } from '../../../shared/ui/form-message.component';
import { IconComponent } from '../../../shared/ui/icon.component';
import { entityIconValidator } from '../../../shared/ledger/entity-icon-validator';

type Entity = LedgerAccount | LedgerCurrency;
type Presentation = 'dialog' | 'panel';

@Component({
  selector: 'app-entity-editor',
  imports: [ReactiveFormsModule, IconComponent, EntityBadgeComponent, LedgerAppearanceFieldsComponent, FieldErrorComponent, FormMessageComponent],
  templateUrl: './entity-editor.component.html',
  styleUrl: './entity-editor.component.scss',
  host: {
    '[class.currency-section]': "kind() === 'currency'",
    '[class.panel-presentation]': "presentation() === 'panel'",
  },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityEditorComponent {
  private readonly fb = inject(FormBuilder);
  private readonly entities = inject(LedgerEntitiesService);
  private readonly errors = inject(ApiErrorService);
  private readonly preferences = inject(PreferencesService);
  private readonly destroyRef = inject(DestroyRef);
  readonly i18n = inject(I18nService);
  readonly kind = input.required<'account' | 'currency'>();
  readonly ledgerUuid = input.required<string>();
  readonly entity = input<Entity | null>(null);
  readonly currencies = input<LedgerCurrency[]>([]);
  readonly presentation = input<Presentation>('dialog');
  readonly close = output<void>();
  readonly saved = output<Entity>();
  readonly deleteRequested = output<Entity>();
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    note: ['', [Validators.maxLength(300)]],
    currency_uuid: [''],
    prefix: ['', [Validators.maxLength(10)]],
    suffix: ['', [Validators.maxLength(10)]],
    decimal_places: [2, [Validators.required, Validators.min(0), Validators.max(20), Validators.pattern(/^\d+$/)]],
    icon: ['lucide:WalletCards', [entityIconValidator]],
    color_code: ['#21E683', [Validators.required, Validators.pattern(/^#[0-9A-Fa-f]{6}$/)]],
  });
  readonly values = signal(this.form.getRawValue());
  readonly maxName = computed(() => this.kind() === 'account' ? 50 : 30);
  readonly title = computed(() => this.i18n.t(this.kind() === 'account'
    ? (this.entity() ? 'accounts.edit' : 'accounts.create')
    : (this.entity() ? 'currencies.edit' : 'currencies.create')));
  readonly currencyName = computed(() => {
    const entity = this.entity();
    return entity && 'currency_uuid' in entity ? this.currencies().find(c => c.uuid === entity.currency_uuid)?.name ?? entity.currency_uuid : '';
  });
  readonly previewColor = computed(() => /^#[0-9A-Fa-f]{6}$/.test(this.values().color_code) ? this.values().color_code : 'var(--token-accent)');
  readonly currencyPreview = computed(() => formatCurrencyPreview(this.values(), this.preferences.current().number_format));

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.values.set(this.form.getRawValue()));
    effect(() => {
      const entity = this.entity(), kind = this.kind();
      untracked(() => {
        const account = entity && 'currency_uuid' in entity ? entity : null;
        const currency = entity && 'decimal_places' in entity ? entity : null;
        this.form.controls.name.setValidators([Validators.required, Validators.maxLength(kind === 'account' ? 50 : 30), Validators.pattern(/\S/)]);
        this.form.controls.currency_uuid.setValidators(kind === 'account' ? [Validators.required] : []);
        this.form.reset({
          name: entity?.name ?? '', note: account?.note ?? '', currency_uuid: account?.currency_uuid ?? '',
          prefix: currency?.prefix ?? '', suffix: currency?.suffix ?? '', decimal_places: currency?.decimal_places ?? 2,
          icon: entity?.icon ?? (kind === 'account' ? 'lucide:WalletCards' : 'lucide:Coins'),
          color_code: entity?.color_code ?? (kind === 'account' ? '#21E683' : '#FFD51A'),
        });
        this.error.set(null);
      });
    });
  }

  @HostListener('document:keydown.escape', ['$event'])
  escape(event: Event): void {
    // The icon picker consumes Escape first.
    if (!event.defaultPrevented) this.requestClose();
  }

  requestClose(): void { if (!this.saving()) this.close.emit(); }

  fieldError(name: keyof typeof this.form.controls): string | null {
    const control = this.form.controls[name];
    if (!(control.dirty || control.touched) || control.valid) return null;
    if (control.hasError('required')) return this.i18n.t('validation.required');
    if (control.hasError('maxlength')) return this.i18n.t('validation.ledgerNameMax', { max: control.getError('maxlength').requiredLength });
    if (name === 'icon') return this.i18n.t('validation.ledgerIconUnicode');
    if (name === 'color_code') return this.i18n.t('validation.ledgerColor');
    if (name === 'decimal_places') return this.i18n.t('validation.decimalPlaces');
    return this.i18n.t('validation.required');
  }

  save(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid || this.saving()) return;
    const value = this.form.getRawValue(), current = this.entity(), uuid = this.ledgerUuid();
    const common = { name: value.name.trim(), icon: value.icon, color_code: value.color_code.toUpperCase() };
    let request: Observable<Entity>;
    if (this.kind() === 'account') {
      const payload = { ...common, note: value.note || null };
      request = current ? this.entities.updateAccount(uuid, current.uuid, payload)
        : this.entities.createAccount(uuid, { ...payload, currency_uuid: value.currency_uuid });
    } else {
      // Formatting affixes can intentionally contain spaces.
      const payload = { ...common, prefix: value.prefix || null, suffix: value.suffix || null };
      request = current ? this.entities.updateCurrency(uuid, current.uuid, payload)
        : this.entities.createCurrency(uuid, { ...payload, decimal_places: value.decimal_places });
    }
    this.saving.set(true);
    this.error.set(null);
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving.set(false))).subscribe({
      next: entity => this.saved.emit(entity),
      error: error => this.error.set(this.errors.message(error, this.kind() === 'account' ? 'errors.accountSaveFailed' : 'errors.currencySaveFailed')),
    });
  }
}
