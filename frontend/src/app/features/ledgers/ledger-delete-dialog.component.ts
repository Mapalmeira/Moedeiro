import { ChangeDetectionStrategy, Component, HostListener, effect, inject, input, output, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../core/api/api-error';
import { I18nService } from '../../core/i18n/i18n.service';
import { Ledger } from '../../core/ledgers/ledger.models';
import { LedgerService } from '../../core/ledgers/ledger.service';
import { FormMessageComponent } from '../../shared/ui/form-message.component';
import { IconComponent } from '../../shared/ui/icon.component';

@Component({
  selector: 'app-ledger-delete-dialog',
  standalone: true,
  imports: [FormsModule, FormMessageComponent, IconComponent],
  template: `
    @if (open()) {
      @if (ledger(); as current) {
        <div class="dialog-backdrop ui-dialog-backdrop" (click)="requestClose()" aria-hidden="true"></div>
        <div class="dialog-layer ui-dialog-layer">
        <div class="ui-dialog-frame ui-projected-surface ui-projection--dialog">
        <section class="dialog ui-dialog-surface" role="alertdialog" aria-modal="true" [attr.aria-label]="i18n.t('ledgers.delete.title')">
        <header class="dialog__header ui-dialog-header">
          <div class="dialog__title ui-dialog-title">
            <span class="title-icon"><app-icon name="trash" [size]="21" /></span>
            <h2>{{ i18n.t('ledgers.delete.title') }}</h2>
          </div>
          <button class="icon-button" type="button" (click)="requestClose()" [disabled]="deleting()"
            [attr.aria-label]="i18n.t('common.close')">
            <app-icon name="x" [size]="19" />
          </button>
        </header>

        <div class="dialog__body ui-delete-dialog-body">
          <app-form-message [text]="i18n.t('ledgers.delete.warning')" />
          <label class="field">
            <span>{{ i18n.t('ledgers.delete.repeatName', { name: current.name }) }}</span>
            <input type="text" [ngModel]="confirmation()" (ngModelChange)="confirmation.set($event)" autocomplete="off" />
          </label>
          @if (errorMessage()) { <app-form-message [text]="errorMessage()!" /> }
          <footer class="dialog__footer ui-surface-actions">
            <button class="ui-button ui-button--danger" type="button" (click)="deleteLedger()" [disabled]="confirmation() !== current.name || deleting()">
              {{ i18n.t('ledgers.delete.confirm') }}
            </button>
          </footer>
        </div>
        </section>
        </div>
        </div>
      }
    }
  `,
  styles: `
    .dialog-layer { --dialog-width: 520px; }
    .dialog {
      --token-accent: var(--danger-token); --token-accent-strong: var(--danger); --focus-accent: var(--danger-token);
    }
    .title-icon { width: var(--compact-title-icon-size); height: var(--compact-title-icon-size); border-color: var(--danger); background: var(--danger-token); color: var(--on-danger-token); }
    .dialog__footer .ui-button { min-width: var(--action-button-min-width); }
    @media (max-width: 460px) { .dialog__footer .ui-button { width: 100%; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerDeleteDialogComponent {
  private readonly ledgers = inject(LedgerService);
  private readonly apiErrors = inject(ApiErrorService);
  readonly i18n = inject(I18nService);

  readonly open = input(false);
  readonly ledger = input<Ledger | null>(null);
  readonly close = output<void>();
  readonly deleted = output<string>();

  readonly confirmation = signal('');
  readonly deleting = signal(false);
  readonly errorMessage = signal<string | null>(null);

  constructor() {
    effect(() => {
      if (this.open()) untracked(() => {
        this.confirmation.set('');
        this.errorMessage.set(null);
      });
    });
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open()) this.requestClose();
  }

  deleteLedger(): void {
    const ledger = this.ledger();
    if (!ledger || this.confirmation() !== ledger.name || this.deleting()) return;

    this.deleting.set(true);
    this.errorMessage.set(null);
    this.ledgers.delete(ledger.uuid).pipe(finalize(() => this.deleting.set(false))).subscribe({
      next: () => {
        this.deleted.emit(ledger.uuid);
        this.close.emit();
      },
      error: (error: unknown) => this.errorMessage.set(this.apiErrors.message(error, 'errors.ledgerDeleteFailed')),
    });
  }

  requestClose(): void {
    if (this.deleting()) return;
    this.close.emit();
  }
}
