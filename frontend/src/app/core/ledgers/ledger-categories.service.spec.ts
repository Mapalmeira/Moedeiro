import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
import { LedgerCategoryPayload } from './ledger-categories.models';
import { LedgerCategoriesService } from './ledger-categories.service';

describe('LedgerCategoriesService', () => {
  const payload: LedgerCategoryPayload = { name: 'Food', icon: 'lucide:Utensils', color_code: '#FFD51A', parent_uuid: null };
  let service: LedgerCategoriesService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(LedgerCategoriesService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads the category tree', () => {
    service.getTree('ledger').subscribe();
    const request = http.expectOne(API_ROUTES.ledgers.categories.tree('ledger'));
    expect(request.request.method).toBe('GET');
    request.flush([]);
  });

  it('creates and updates categories with the same payload contract', () => {
    service.create('ledger', payload).subscribe();
    const creation = http.expectOne(API_ROUTES.ledgers.categories.root('ledger'));
    expect(creation.request.method).toBe('POST');
    expect(creation.request.body).toEqual(payload);
    creation.flush({ uuid: 'category', ...payload });

    service.update('ledger', 'category', { ...payload, parent_uuid: 'parent' }).subscribe();
    const update = http.expectOne(API_ROUTES.ledgers.categories.byUuid('ledger', 'category'));
    expect(update.request.method).toBe('PUT');
    expect(update.request.body).toEqual({ ...payload, parent_uuid: 'parent' });
    update.flush({ uuid: 'category', ...payload, parent_uuid: 'parent' });
  });

  it('deletes a category by identifier', () => {
    service.delete('ledger', 'category').subscribe();
    const request = http.expectOne(API_ROUTES.ledgers.categories.byUuid('ledger', 'category'));
    expect(request.request.method).toBe('DELETE');
    request.flush(null);
  });
});
