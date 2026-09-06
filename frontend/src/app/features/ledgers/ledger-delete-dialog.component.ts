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
        <div class="dialog-backdrop" (click)="requestClose()" aria-hidden="true"></div>
        <section class="dialog" role="alertdialog" aria-modal="true" [attr.aria-label]="i18n.t('ledgers.delete.title')">
        <header class="dialog__header">
          <div class="dialog__title">
            <span class="title-icon"><app-icon name="trash" [size]="21" /></span>
            <h2>{{ i18n.t('ledgers.delete.title') }}</h2>
          </div>
          <button class="icon-button" type="button" (click)="requestClose()" [disabled]="deleting()"
            [attr.aria-label]="i18n.t('common.close')">
            <app-icon name="x" [size]="19" />
          </button>
        </header>

        <div class="dialog__body">
          <p>{{ i18n.t('ledgers.delete.warning') }}</p>
          <label class="field">
            <span>{{ i18n.t('ledgers.delete.repeatName', { name: current.name }) }}</span>
            <input type="text" [ngModel]="confirmation()" (ngModelChange)="confirmation.set($event)" autocomplete="off" />
          </label>
          @if (errorMessage()) { <app-form-message [text]="errorMessage()!" /> }
          <footer class="dialog__footer">
            <button class="ui-button ui-button--danger" type="button" (click)="deleteLedger()" [disabled]="confirmation() !== current.name || deleting()">
              {{ deleting() ? i18n.t('ledgers.delete.deleting') : i18n.t('ledgers.delete.confirm') }}
            </button>
          </footer>
        </div>
        </section>
      }
    }
  `,
  styles: `
    .dialog-backdrop { position: fixed; inset: 0; z-index: 60; background: rgb(0 0 0 / .38); backdrop-filter: blur(2px); }
    .dialog {
      --token-accent: var(--danger-token); --token-accent-strong: var(--danger); --focus-accent: var(--danger-token);
      position: fixed; z-index: 61; top: 50%; left: 50%; width: min(520px, calc(100vw - 28px));
      max-height: calc(100dvh - 30px); overflow: auto; transform: translate(-50%, -50%);
      border: 2px solid var(--line-strong); border-radius: var(--radius-card); background: var(--surface); color: var(--text);
      filter: var(--dialog-shadow);
    }
    .dialog__header { display: flex; align-items: center; justify-content: space-between; gap: var(--form-gap); padding: 17px 19px; border-bottom: 2px solid var(--line); }
    .dialog__title { display: flex; align-items: center; gap: var(--title-icon-gap); }
    .dialog__title h2 { margin: 0; font-size: 1.22rem; }
    .title-icon { width: 40px; height: 40px; display: grid; place-items: center; border: 1.5px solid var(--danger); border-radius: 5px; background: var(--danger-token); color: var(--on-danger-token); }
    .dialog__body { display: grid; gap: var(--section-gap); padding: var(--space-5); }
    p { margin: 0; color: var(--text-muted); line-height: 1.55; }
    .dialog__footer { display: flex; justify-content: flex-end; }
    .dialog__footer .ui-button { min-width: 180px; }
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
