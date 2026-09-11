import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
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

  it('requests the currency overview at the selected reference timestamp', () => {
    service.currencyOverview('ledger', 'currency', 1_775_001_599, 3).subscribe();

    const request = http.expectOne(candidate => candidate.url === `${API_ROUTES.ledgerBudgets('ledger')}/currency-overview`);
    expect(request.request.method).toBe('GET');
    expect(request.request.params.get('currency_uuid')).toBe('currency');
    expect(request.request.params.get('timestamp')).toBe('1775001599');
    expect(request.request.params.get('limit')).toBe('3');
    request.flush([]);
  });
});
