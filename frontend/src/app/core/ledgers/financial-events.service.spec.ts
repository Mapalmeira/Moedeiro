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

    const request = http.expectOne(candidate => candidate.url === API_ROUTES.ledgerEvents('ledger/id'));
    expect(request.request.params.get('description_search')).toBe('dinner');
    expect(request.request.withCredentials).toBe(true);
    request.flush({ events: [], next_cursor: null, total_count: 0 });
  });
});
