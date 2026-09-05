import { ChangeDetectionStrategy, Component, effect, inject, input, signal } from '@angular/core';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { LedgerService } from '../../core/ledgers/ledger.service';

@Component({
  selector: 'app-ledger-page',
  standalone: true,
  template: `<section class="ledger-placeholder" [attr.aria-busy]="loading()"></section>`,
  styles: `.ledger-placeholder { width: 100%; min-height: 420px; }`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerPageComponent {
  private readonly ledgers = inject(LedgerService);
  private readonly router = inject(Router);

  readonly ledgerUuid = input.required<string>();
  readonly loading = signal(false);

  constructor() {
    effect(() => {
      const ledgerUuid = this.ledgerUuid();
      this.loading.set(true);
      this.ledgers.access(ledgerUuid).pipe(finalize(() => this.loading.set(false))).subscribe({
        error: () => void this.router.navigate(['/home']),
      });
    });
  }
}
