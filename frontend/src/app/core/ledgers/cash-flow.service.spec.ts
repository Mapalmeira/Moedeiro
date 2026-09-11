import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
import { CashFlowService } from './cash-flow.service';

describe('CashFlowService', () => {
  let service: CashFlowService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(CashFlowService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('requests a summary with the applied activity filters and credentials', () => {
    service.summary('ledger/id', 'currency', {
      from_timestamp: 10,
      to_timestamp: 20,
      account_uuid: 'account',
      category_uuid: 'category',
      event_type: 'TRANSACTION',
      description_search: 'dinner',
    }).subscribe();

    const request = http.expectOne(candidate => candidate.url === API_ROUTES.ledgers.cashFlow.root('ledger/id'));
    expect(request.request.method).toBe('GET');
    expect(request.request.params.get('currency_uuid')).toBe('currency');
    expect(request.request.params.get('from_timestamp')).toBe('10');
    expect(request.request.params.get('to_timestamp')).toBe('20');
    expect(request.request.params.get('account_uuid')).toBe('account');
    expect(request.request.params.get('category_uuid')).toBe('category');
    expect(request.request.params.get('event_type')).toBe('TRANSACTION');
    expect(request.request.params.get('description_search')).toBe('dinner');
    request.flush({});
  });

  it('requests points with the applied filters and credentials', () => {
    service.points('ledger/id', 'currency', 10, 20, 5, { account_uuid: 'account' }).subscribe();

    const request = http.expectOne(candidate => candidate.url === API_ROUTES.ledgers.cashFlow.points('ledger/id'));
    expect(request.request.method).toBe('GET');
    expect(request.request.params.get('currency_uuid')).toBe('currency');
    expect(request.request.params.get('from_timestamp')).toBe('10');
    expect(request.request.params.get('to_timestamp')).toBe('20');
    expect(request.request.params.get('point_width')).toBe('5');
    expect(request.request.params.get('account_uuid')).toBe('account');
    request.flush([]);
  });

  it('requests a Sankey graph for one account and detail level', () => {
    service.sankey('ledger/id', 'account', 100, 200, 3).subscribe();

    const request = http.expectOne(candidate => candidate.url === API_ROUTES.ledgers.cashFlow.sankey('ledger/id'));
    expect(request.request.method).toBe('GET');
    expect(request.request.params.get('account_uuid')).toBe('account');
    expect(request.request.params.get('from_timestamp')).toBe('100');
    expect(request.request.params.get('to_timestamp')).toBe('200');
    expect(request.request.params.get('detail_level')).toBe('3');
    request.flush({});
  });
});
