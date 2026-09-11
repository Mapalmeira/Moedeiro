import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, output, signal, untracked } from '@angular/core';
import { DialogShellComponent } from '../../../../shared/ui/dialog-shell.component';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerCategory } from '../../../../core/ledgers/ledger-categories.models';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { EntityBadgeComponent } from '../../../../shared/ledger/entity-badge.component';
import { entityIconValidator } from '../../../../shared/ledger/entity-icon-validator';
import { LedgerAppearanceFieldsComponent } from '../../../../shared/ledger/ledger-appearance-fields.component';
import { DEFAULT_CATEGORY_APPEARANCE, HEX_COLOR_PATTERN, isHexColor } from '../../../../shared/ledger/ledger-appearance';
import { FieldErrorComponent } from '../../../../shared/ui/field-error.component';
import { FormMessageComponent } from '../../../../shared/ui/form-message.component';
import { IconComponent } from '../../../../shared/ui/icon.component';
import { CategoryParentSelectComponent, ROOT_CATEGORY_VALUE } from './category-parent-select.component';


@Component({
  selector: 'app-category-editor',
  standalone: true,
  imports: [DialogShellComponent, 
    ReactiveFormsModule,
    CategoryParentSelectComponent,
    EntityBadgeComponent,
    LedgerAppearanceFieldsComponent,
    FieldErrorComponent,
    FormMessageComponent,
    IconComponent,
  ],
  templateUrl: './category-editor.component.html',
  styleUrl: './category-editor.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CategoryEditorComponent {
  private readonly fb = inject(FormBuilder);
  private readonly categoriesService = inject(LedgerCategoriesService);
  private readonly errors = inject(ApiErrorService);
  private readonly destroyRef = inject(DestroyRef);
  readonly i18n = inject(I18nService);

  readonly ledgerUuid = input.required<string>();
  readonly category = input<LedgerCategory | null>(null);
  readonly categories = input.required<readonly LedgerCategory[]>();
  readonly initialParentUuid = input<string | null>(null);
  readonly close = output<void>();
  readonly saved = output<LedgerCategory>();
  readonly deleteRequested = output<LedgerCategory>();

  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(30), Validators.pattern(/\S/)]],
    parent: [ROOT_CATEGORY_VALUE, [Validators.required]],
    icon: [DEFAULT_CATEGORY_APPEARANCE.icon, [entityIconValidator]],
    color_code: [DEFAULT_CATEGORY_APPEARANCE.color, [Validators.required, Validators.pattern(HEX_COLOR_PATTERN)]],
  });
  readonly values = signal(this.form.getRawValue());
  readonly title = computed(() => this.i18n.t(this.category() ? 'categories.edit' : 'categories.create'));
  readonly previewColor = computed(() => isHexColor(this.values().color_code) ? this.values().color_code : DEFAULT_CATEGORY_APPEARANCE.color);
  readonly excludedParentUuids = computed(() => {
    const current = this.category();
    if (!current) return new Set<string>();

    const childrenByParent = new Map<string, string[]>();
    for (const category of this.categories()) {
      if (!category.parent_uuid) continue;
      const children = childrenByParent.get(category.parent_uuid) ?? [];
      children.push(category.uuid);
      childrenByParent.set(category.parent_uuid, children);
    }

    const excluded = new Set<string>();
    const pending = [current.uuid];
    while (pending.length > 0) {
      const uuid = pending.pop();
      if (!uuid || excluded.has(uuid)) continue;
      excluded.add(uuid);
      pending.push(...(childrenByParent.get(uuid) ?? []));
    }
    return excluded;
  });

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.values.set(this.form.getRawValue()));
    effect(() => {
      const category = this.category();
      const initialParentUuid = this.initialParentUuid();
      untracked(() => {
        this.form.reset({
          name: category?.name ?? '',
          parent: (category?.parent_uuid ?? initialParentUuid) || ROOT_CATEGORY_VALUE,
          icon: category?.icon ?? DEFAULT_CATEGORY_APPEARANCE.icon,
          color_code: category?.color_code ?? DEFAULT_CATEGORY_APPEARANCE.color,
        });
        this.error.set(null);
      });
    });
  }

  requestClose(): void {
    if (!this.saving()) this.close.emit();
  }

  setParent(value: string): void {
    this.form.controls.parent.setValue(value);
    this.form.controls.parent.markAsDirty();
  }

  fieldError(name: keyof typeof this.form.controls): string | null {
    const control = this.form.controls[name];
    if (!(control.dirty || control.touched) || control.valid) return null;
    if (control.hasError('required')) return this.i18n.t('validation.required');
    if (control.hasError('maxlength')) return this.i18n.t('validation.ledgerNameMax', { max: 30 });
    if (name === 'icon') return this.i18n.t('validation.ledgerIconUnicode');
    if (name === 'color_code') return this.i18n.t('validation.ledgerColor');
    return this.i18n.t('validation.required');
  }

  save(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid || this.saving()) return;

    const value = this.form.getRawValue();
    const current = this.category();
    const payload = {
      name: value.name.trim(),
      parent_uuid: value.parent === ROOT_CATEGORY_VALUE ? null : value.parent,
      icon: value.icon,
      color_code: value.color_code.toUpperCase(),
    };
    const request = current
      ? this.categoriesService.update(this.ledgerUuid(), current.uuid, payload)
      : this.categoriesService.create(this.ledgerUuid(), payload);

    this.saving.set(true);
    this.error.set(null);
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving.set(false))).subscribe({
      next: category => this.saved.emit(category),
      error: error => this.error.set(this.errors.message(error, 'errors.categorySaveFailed')),
    });
  }
}
