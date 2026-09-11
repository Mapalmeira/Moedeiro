import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
import { Ledger } from './ledger.models';
import { LedgerService } from './ledger.service';

const firstLedger: Ledger = {
  uuid: '11111111-1111-1111-1111-111111111111',
  name: 'Personal',
  icon: 'unicode:R$',
  color_code: '#21E683',
  last_accessed_at: 1,
};

const secondLedger: Ledger = {
  uuid: '22222222-2222-2222-2222-222222222222',
  name: 'Company',
  icon: 'lucide:Building2',
  color_code: '#488DFC',
  last_accessed_at: 2,
};

describe('LedgerService', () => {
  let service: LedgerService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(LedgerService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('replaces the ledger state when listing ledgers', () => {
    service.list().subscribe();
    http.expectOne(API_ROUTES.ledgers.root).flush([firstLedger, secondLedger]);

    expect(service.ledgers()).toEqual([firstLedger, secondLedger]);
  });

  it('adds an accessed ledger to an empty state when opened directly by URL', () => {
    service.access(firstLedger.uuid).subscribe();
    http.expectOne(API_ROUTES.ledgers.byUuid(firstLedger.uuid)).flush(firstLedger);

    expect(service.ledgers()).toEqual([firstLedger]);
  });

  it('replaces an existing ledger after access or update instead of duplicating it', () => {
    service.list().subscribe();
    http.expectOne(API_ROUTES.ledgers.root).flush([firstLedger]);

    const updated = { ...firstLedger, name: 'Updated' };
    service.update(firstLedger.uuid, { name: updated.name, icon: updated.icon, color_code: updated.color_code }).subscribe();
    http.expectOne(API_ROUTES.ledgers.byUuid(firstLedger.uuid)).flush(updated);

    expect(service.ledgers()).toEqual([updated]);
  });

  it('prepends a newly created ledger', () => {
    service.list().subscribe();
    http.expectOne(API_ROUTES.ledgers.root).flush([firstLedger]);

    service.create({ name: secondLedger.name, icon: secondLedger.icon, color_code: secondLedger.color_code }).subscribe();
    http.expectOne(API_ROUTES.ledgers.root).flush(secondLedger);

    expect(service.ledgers()).toEqual([secondLedger, firstLedger]);
  });

  it('removes a ledger from state after deletion', () => {
    service.list().subscribe();
    http.expectOne(API_ROUTES.ledgers.root).flush([firstLedger, secondLedger]);

    service.delete(firstLedger.uuid).subscribe();
    http.expectOne(API_ROUTES.ledgers.byUuid(firstLedger.uuid)).flush(null);

    expect(service.ledgers()).toEqual([secondLedger]);
  });
});
