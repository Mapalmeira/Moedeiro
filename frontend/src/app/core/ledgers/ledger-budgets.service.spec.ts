import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
import { CreateLedgerBudgetPayload } from './ledger-budgets.models';
import { LedgerBudgetsService } from './ledger-budgets.service';

describe('LedgerBudgetsService', () => {
  let service: LedgerBudgetsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(LedgerBudgetsService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('builds an overview query from active filters and omits blank search', () => {
    service.overview('ledger', {
      states: ['ACTIVE', 'FUTURE'], pageSize: 20, search: '  food  ', accountUuid: 'account', categoryUuid: 'category', cursor: 'next',
    }).subscribe();

    const request = http.expectOne(candidate => candidate.url === API_ROUTES.ledgers.budgets.overview('ledger'));
    expect(request.request.params.getAll('state')).toEqual(['ACTIVE', 'FUTURE']);
    expect(request.request.params.get('page_size')).toBe('20');
    expect(request.request.params.get('search')).toBe('food');
    expect(request.request.params.get('account_uuid')).toBe('account');
    expect(request.request.params.get('category_uuid')).toBe('category');
    expect(request.request.params.get('cursor')).toBe('next');
    request.flush({ items: [], next_cursor: null });

    service.overview('ledger', { states: [], pageSize: 10, search: '   ' }).subscribe();
    const minimal = http.expectOne(candidate => candidate.url === API_ROUTES.ledgers.budgets.overview('ledger'));
    expect(minimal.request.params.keys()).toEqual(['page_size']);
    minimal.flush({ items: [], next_cursor: null });
  });

  it('requests the currency overview at the selected reference timestamp', () => {
    service.currencyOverview('ledger', 'currency', 1_775_001_599, 3).subscribe();

    const request = http.expectOne(candidate => candidate.url === API_ROUTES.ledgers.budgets.currencyOverview('ledger'));
    expect(request.request.method).toBe('GET');
    expect(request.request.params.get('currency_uuid')).toBe('currency');
    expect(request.request.params.get('timestamp')).toBe('1775001599');
    expect(request.request.params.get('limit')).toBe('3');
    request.flush([]);
  });

  it('gets, creates, updates, and deletes a budget through its resource routes', () => {
    const payload: CreateLedgerBudgetPayload = {
      account_uuid: 'account', category_uuid: 'category', from_timestamp: 10, to_timestamp: 20, name: 'Food', description: null, amount: 100,
    };

    service.get('ledger', 'budget').subscribe();
    http.expectOne(API_ROUTES.ledgers.budgets.byUuid('ledger', 'budget')).flush({ uuid: 'budget', ...payload });

    service.create('ledger', payload).subscribe();
    const creation = http.expectOne(API_ROUTES.ledgers.budgets.root('ledger'));
    expect(creation.request.method).toBe('POST');
    expect(creation.request.body).toEqual(payload);
    creation.flush({ uuid: 'budget', ...payload });

    const updatePayload = { ...payload, name: 'Updated' };
    const { account_uuid: _, ...mutablePayload } = updatePayload;
    service.update('ledger', 'budget', mutablePayload).subscribe();
    const update = http.expectOne(API_ROUTES.ledgers.budgets.byUuid('ledger', 'budget'));
    expect(update.request.method).toBe('PUT');
    expect(update.request.body).toEqual(mutablePayload);
    update.flush({ uuid: 'budget', ...updatePayload });

    service.delete('ledger', 'budget').subscribe();
    const deletion = http.expectOne(API_ROUTES.ledgers.budgets.byUuid('ledger', 'budget'));
    expect(deletion.request.method).toBe('DELETE');
    deletion.flush(null);
  });
});
