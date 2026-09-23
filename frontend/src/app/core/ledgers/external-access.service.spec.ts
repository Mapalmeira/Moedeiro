import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_ROUTES } from '../api/api.routes';
import { CreatedExternalAccessGrant, ExternalAccessGrant } from './external-access.models';
import { ExternalAccessService } from './external-access.service';

const ledgerUuid = '11111111-1111-1111-1111-111111111111';
const grant: ExternalAccessGrant = {
  grant_uuid: '22222222-2222-2222-2222-222222222222',
  external_access_uuid: '33333333-3333-3333-3333-333333333333',
  name: 'Sync plugin',
  created_at: 1_700_000_000,
};

describe('ExternalAccessService', () => {
  let service: ExternalAccessService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ExternalAccessService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists external accesses for a ledger', () => {
    let result: ExternalAccessGrant[] | undefined;
    service.list(ledgerUuid).subscribe((value) => result = value);

    http.expectOne(API_ROUTES.ledgers.externalAccesses.root(ledgerUuid)).flush([grant]);

    expect(result).toEqual([grant]);
  });

  it('creates an external access with credentials', () => {
    const payload = { name: 'Sync plugin', current_password: 'password123', totp_code: '123456' };
    const created: CreatedExternalAccessGrant = { ...grant, token: 'one-time-token' };
    let result: CreatedExternalAccessGrant | undefined;

    service.create(ledgerUuid, payload).subscribe((value) => result = value);

    const request = http.expectOne(API_ROUTES.ledgers.externalAccesses.root(ledgerUuid));
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(payload);
    request.flush(created);
    expect(result).toEqual(created);
  });

  it('revokes an external access grant with credentials in the delete body', () => {
    const payload = { current_password: 'password123', totp_code: null };
    service.revoke(ledgerUuid, grant.grant_uuid, payload).subscribe();

    const request = http.expectOne(API_ROUTES.ledgers.externalAccesses.byGrantUuid(ledgerUuid, grant.grant_uuid));
    expect(request.request.method).toBe('DELETE');
    expect(request.request.body).toEqual(payload);
    request.flush(null);
  });
});
