import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../core/api/api-error';
import { I18nService } from '../../../core/i18n/i18n.service';
import { LedgerAccount, LedgerCurrency } from '../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../core/ledgers/ledger-entities.service';
import { LedgerContextService } from '../../../core/ledgers/ledger-context.service';
import { LedgerWorkspaceStateService } from '../../../core/ledgers/ledger-workspace-state.service';
import { LedgerEntityManagerComponent } from './ledger-entity-manager.component';

const currency: LedgerCurrency = { uuid: 'currency', name: 'Real', prefix: 'R$ ', suffix: null, decimal_places: 2, icon: 'lucide:Coins', color_code: '#FFD51A' };
const account: LedgerAccount = { uuid: 'account', name: 'Checking', note: 'Main', currency_uuid: currency.uuid, icon: 'lucide:Wallet', color_code: '#21E683' };

describe('LedgerEntityManagerComponent', () => {
  const ledgerUuid = signal('ledger');
  const entities = {
    listAccounts: vi.fn(() => of([account])), listCurrencies: vi.fn(() => of([currency])),
    listBalances: vi.fn(() => of({ items: [{ account_uuid: 'account', currency_uuid: 'currency', balance: 1234 }], total_balance: 1234 })),
    deleteAccount: vi.fn(() => of(void 0)), deleteCurrency: vi.fn(() => of(void 0)),
  };
  const workspace = { getEntitySearch: vi.fn(() => ''), setEntitySearch: vi.fn() };

  beforeEach(() => {
    vi.clearAllMocks();
    ledgerUuid.set('ledger');
    entities.listAccounts.mockReturnValue(of([account]));
    entities.listCurrencies.mockReturnValue(of([currency]));
    entities.listBalances.mockReturnValue(of({ items: [{ account_uuid: 'account', currency_uuid: 'currency', balance: 1234 }], total_balance: 1234 }));
    entities.deleteAccount.mockReturnValue(of(void 0));
    entities.deleteCurrency.mockReturnValue(of(void 0));
    TestBed.configureTestingModule({
      imports: [LedgerEntityManagerComponent],
      providers: [
        { provide: LedgerEntitiesService, useValue: entities },
        { provide: LedgerContextService, useValue: { ledgerUuid: ledgerUuid.asReadonly() } },
        { provide: LedgerWorkspaceStateService, useValue: workspace },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'operation failed') } },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
  });

  function createManager(kind: 'account' | 'currency'): ComponentFixture<LedgerEntityManagerComponent> {
    const fixture = TestBed.createComponent(LedgerEntityManagerComponent);
    fixture.componentRef.setInput('kind', kind);
    fixture.detectChanges();
    return fixture;
  }

  it('loads account rows with their currency and point-in-time balance', () => {
    const fixture = createManager('account');

    expect(entities.listAccounts).toHaveBeenCalledWith('ledger');
    expect(entities.listCurrencies).toHaveBeenCalledWith('ledger');
    expect(fixture.componentInstance.rows()[0]).toEqual(expect.objectContaining({ item: account, detailText: 'Main', balance: 1234, balanceText: 'R$ 12.34' }));
  });

  it('aggregates account balances for a currency row', () => {
    entities.listBalances.mockReturnValue(of({
      items: [
        { account_uuid: 'one', currency_uuid: 'currency', balance: 100 },
        { account_uuid: 'two', currency_uuid: 'currency', balance: 250 },
      ],
      total_balance: 350,
    }));
    const fixture = createManager('currency');

    expect(entities.listAccounts).not.toHaveBeenCalled();
    expect(fixture.componentInstance.rows()[0]).toEqual(expect.objectContaining({ item: currency, balance: 350, balanceText: 'R$ 3.50' }));
  });

  it('persists search per ledger and filters accent-insensitively', () => {
    const fixture = createManager('account');
    fixture.componentInstance.filter({ target: { value: 'check' } } as unknown as Event);

    expect(workspace.setEntitySearch).toHaveBeenCalledWith('ledger', 'account', 'check');
    expect(fixture.componentInstance.filtered()).toEqual([account]);
  });

  it('deletes the selected account and reloads the collection', () => {
    const fixture = createManager('account');
    fixture.componentInstance.confirmDelete(account);
    entities.listAccounts.mockClear();

    fixture.componentInstance.remove();

    expect(entities.deleteAccount).toHaveBeenCalledWith('ledger', 'account');
    expect(fixture.componentInstance.deleting()).toBeNull();
    expect(entities.listAccounts).toHaveBeenCalledWith('ledger');
  });

  it('keeps delete confirmation open after a failure', () => {
    entities.deleteCurrency.mockReturnValue(throwError(() => new Error('in use')));
    const fixture = createManager('currency');
    fixture.componentInstance.confirmDelete(currency);

    fixture.componentInstance.remove();

    expect(fixture.componentInstance.deleting()).toBe(currency);
    expect(fixture.componentInstance.deleteError()).toBe('operation failed');
    expect(fixture.componentInstance.deletingBusy()).toBe(false);
  });
});
