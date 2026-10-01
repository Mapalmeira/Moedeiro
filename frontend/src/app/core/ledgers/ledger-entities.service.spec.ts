import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
import { LedgerAccountPayload, LedgerCurrencyPayload } from './ledger-entities.models';
import { LedgerEntitiesService } from './ledger-entities.service';

describe('LedgerEntitiesService', () => {
  let service: LedgerEntitiesService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(LedgerEntitiesService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('uses the account collection contract', () => {
    const payload: LedgerAccountPayload = { name: 'Checking', note: null, currency_uuid: 'currency', icon: 'lucide:Wallet', color_code: '#21E683' };
    service.listAccounts('ledger').subscribe();
    http.expectOne(API_ROUTES.ledgers.accounts.root('ledger')).flush([]);

    service.createAccount('ledger', payload).subscribe();
    const creation = http.expectOne(API_ROUTES.ledgers.accounts.root('ledger'));
    expect(creation.request.method).toBe('POST');
    expect(creation.request.body).toEqual(payload);
    creation.flush({ uuid: 'account', ...payload });
  });

  it('updates and deletes an account without resending its immutable currency', () => {
    const payload = { name: 'Updated', note: 'Note', icon: 'lucide:Wallet', color_code: '#488DFC' };
    service.updateAccount('ledger', 'account', payload).subscribe();
    const update = http.expectOne(API_ROUTES.ledgers.accounts.byUuid('ledger', 'account'));
    expect(update.request.method).toBe('PUT');
    expect(update.request.body).toEqual(payload);
    update.flush({ uuid: 'account', currency_uuid: 'currency', ...payload });

    service.deleteAccount('ledger', 'account').subscribe();
    const deletion = http.expectOne(API_ROUTES.ledgers.accounts.byUuid('ledger', 'account'));
    expect(deletion.request.method).toBe('DELETE');
    deletion.flush(null);
  });

  it('requests point-in-time balances with optional filters only when supplied', () => {
    service.getAccountBalance('ledger', 'account', 100).subscribe();
    const accountBalance = http.expectOne(candidate => candidate.url === API_ROUTES.ledgers.accounts.balance('ledger', 'account'));
    expect(accountBalance.request.params.get('timestamp')).toBe('100');
    accountBalance.flush(250);

    service.listBalances('ledger', 100, null, null).subscribe();
    const unfiltered = http.expectOne(candidate => candidate.url === API_ROUTES.ledgers.balances('ledger'));
    expect(unfiltered.request.params.keys()).toEqual(['timestamp']);
    unfiltered.flush({ items: [], total_balance: null });

    service.listBalances('ledger', 100, 'currency', 5).subscribe();
    const filtered = http.expectOne(candidate => candidate.url === API_ROUTES.ledgers.balances('ledger'));
    expect(filtered.request.params.get('currency_uuid')).toBe('currency');
    expect(filtered.request.params.get('limit')).toBe('5');
    filtered.flush({ items: [], total_balance: 0 });
  });

  it('uses the currency collection contract', () => {
    const payload: LedgerCurrencyPayload = { name: 'Real', prefix: 'R$ ', suffix: null, decimal_places: 2, icon: 'lucide:Coins', color_code: '#FFD51A' };
    service.listCurrencies('ledger').subscribe();
    http.expectOne(API_ROUTES.ledgers.currencies.root('ledger')).flush([]);

    service.createCurrency('ledger', payload).subscribe();
    const creation = http.expectOne(API_ROUTES.ledgers.currencies.root('ledger'));
    expect(creation.request.method).toBe('POST');
    expect(creation.request.body).toEqual(payload);
    creation.flush({ uuid: 'currency', ...payload });
  });

  it('updates and deletes a currency without resending decimal places', () => {
    const payload = { name: 'Real', prefix: 'R$ ', suffix: null, icon: 'lucide:Coins', color_code: '#21E683' };
    service.updateCurrency('ledger', 'currency', payload).subscribe();
    const update = http.expectOne(API_ROUTES.ledgers.currencies.byUuid('ledger', 'currency'));
    expect(update.request.method).toBe('PUT');
    expect(update.request.body).toEqual(payload);
    update.flush({ uuid: 'currency', decimal_places: 2, ...payload });

    service.deleteCurrency('ledger', 'currency').subscribe();
    const deletion = http.expectOne(API_ROUTES.ledgers.currencies.byUuid('ledger', 'currency'));
    expect(deletion.request.method).toBe('DELETE');
    deletion.flush(null);
  });
});
