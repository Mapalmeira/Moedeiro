import { DestroyRef, Injectable, computed, inject, signal } from '@angular/core';
import { Subscription, finalize } from 'rxjs';
import { ApiErrorService } from '../api/api-error';
import { LedgerService } from './ledger.service';

@Injectable()
export class LedgerContextService {
  private readonly ledgers = inject(LedgerService);
  private readonly apiErrors = inject(ApiErrorService);
  private readonly destroyRef = inject(DestroyRef);
  private request: Subscription | null = null;

  readonly ledgerUuid = signal<string | null>(null);
  readonly loading = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly ledger = computed(() => {
    const uuid = this.ledgerUuid();
    return uuid ? this.ledgers.ledgers().find((ledger) => ledger.uuid === uuid) ?? null : null;
  });

  constructor() {
    this.destroyRef.onDestroy(() => this.request?.unsubscribe());
  }

  load(ledgerUuid: string): void {
    if (!ledgerUuid) return;

    this.request?.unsubscribe();
    this.ledgerUuid.set(ledgerUuid);
    this.loading.set(true);
    this.loadError.set(null);

    this.request = this.ledgers.access(ledgerUuid).pipe(
      finalize(() => this.loading.set(false)),
    ).subscribe({
      error: (error: unknown) => {
        this.loadError.set(this.apiErrors.message(error, 'errors.ledgerNotFound'));
      },
    });
  }
}
