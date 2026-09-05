import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of, tap, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../api/api-error';
import { Ledger } from './ledger.models';
import { LedgerContextService } from './ledger-context.service';
import { LedgerService } from './ledger.service';

const ledger: Ledger = {
  uuid: '11111111-1111-1111-1111-111111111111',
  name: 'Personal',
  icon: 'unicode:R$',
  color_code: '#21E683',
  last_accessed_at: 1,
};

describe('LedgerContextService', () => {
  const ledgerState = signal<Ledger[]>([]);
  const ledgerService = {
    ledgers: ledgerState.asReadonly(),
    access: vi.fn((ledgerUuid: string) => of({ ...ledger, uuid: ledgerUuid }).pipe(
      tap((value) => ledgerState.set([value])),
    )),
  };

  beforeEach(() => {
    ledgerState.set([]);
    vi.clearAllMocks();
    ledgerService.access.mockImplementation((ledgerUuid: string) => of({ ...ledger, uuid: ledgerUuid }).pipe(
      tap((value) => ledgerState.set([value])),
    ));

    TestBed.configureTestingModule({
      providers: [
        LedgerContextService,
        { provide: LedgerService, useValue: ledgerService },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'ledger error') } },
      ],
    });
  });

  it('loads the route ledger into the shared ledger context', () => {
    const context = TestBed.inject(LedgerContextService);

    context.load(ledger.uuid);

    expect(ledgerService.access).toHaveBeenCalledWith(ledger.uuid);
    expect(context.ledgerUuid()).toBe(ledger.uuid);
    expect(context.ledger()).toEqual(ledger);
    expect(context.loading()).toBe(false);
    expect(context.loadError()).toBeNull();
  });

  it('exposes a localized load error without inventing a ledger', () => {
    ledgerService.access.mockReturnValueOnce(throwError(() => new Error('missing')));
    const context = TestBed.inject(LedgerContextService);

    context.load(ledger.uuid);

    expect(context.ledger()).toBeNull();
    expect(context.loading()).toBe(false);
    expect(context.loadError()).toBe('ledger error');
  });
});
