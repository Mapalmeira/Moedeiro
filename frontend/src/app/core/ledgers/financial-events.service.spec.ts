import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
import { FinancialEventsService } from './financial-events.service';

describe('FinancialEventsService', () => {
  let service: FinancialEventsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(FinancialEventsService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('includes a trimmed description search in the event query', () => {
    service.list('ledger/id', {
      from_timestamp: 10,
      to_timestamp: 20,
      page_size: 40,
      description_search: '  dinner  ',
    }).subscribe();

    const request = http.expectOne(candidate => candidate.url === API_ROUTES.ledgers.events.root('ledger/id'));
    expect(request.request.params.get('description_search')).toBe('dinner');
    request.flush({ events: [], next_cursor: null, total_count: 0 });
  });

  it('includes every supplied activity filter and stable pagination defaults', () => {
    service.list('ledger', {
      from_timestamp: 10, to_timestamp: 20, page_size: 40, ascending: true,
      account_uuid: 'account', currency_uuid: 'currency', category_uuid: 'category', event_type: 'TRANSACTION', cursor: 'next',
    }).subscribe();

    const request = http.expectOne(candidate => candidate.url === API_ROUTES.ledgers.events.root('ledger'));
    expect(request.request.params.get('from_timestamp')).toBe('10');
    expect(request.request.params.get('to_timestamp')).toBe('20');
    expect(request.request.params.get('page_size')).toBe('40');
    expect(request.request.params.get('ascending')).toBe('true');
    expect(request.request.params.get('account_uuid')).toBe('account');
    expect(request.request.params.get('currency_uuid')).toBe('currency');
    expect(request.request.params.get('category_uuid')).toBe('category');
    expect(request.request.params.get('event_type')).toBe('TRANSACTION');
    expect(request.request.params.get('cursor')).toBe('next');
    request.flush({ events: [], next_cursor: null, total_count: 0 });
  });

  it('uses collection and resource endpoints for event mutations', () => {
    const payload = {
      type: 'TRANSACTION' as const, occurred_at: 10, description: 'Lunch', account_uuid: 'account', category_uuid: 'category', value: -100, quantity: 1, item_name: null, fee: null,
    };

    service.create('ledger', payload).subscribe();
    const creation = http.expectOne(API_ROUTES.ledgers.events.root('ledger'));
    expect(creation.request.method).toBe('POST');
    expect(creation.request.body).toEqual(payload);
    creation.flush({ uuid: 'event', movements: [], ...payload });

    service.update('ledger', 'event', payload).subscribe();
    const update = http.expectOne(API_ROUTES.ledgers.events.byUuid('ledger', 'event'));
    expect(update.request.method).toBe('PUT');
    expect(update.request.body).toEqual(payload);
    update.flush({ uuid: 'event', movements: [], ...payload });

    service.delete('ledger', 'event').subscribe();
    const deletion = http.expectOne(API_ROUTES.ledgers.events.byUuid('ledger', 'event'));
    expect(deletion.request.method).toBe('DELETE');
    deletion.flush(null);
  });
});
