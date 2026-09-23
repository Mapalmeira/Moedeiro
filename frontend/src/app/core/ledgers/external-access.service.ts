import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import {
  CreateExternalAccessRequest,
  CreatedExternalAccessGrant,
  ExternalAccessCredentials,
  ExternalAccessGrant,
} from './external-access.models';

@Injectable({ providedIn: 'root' })
export class ExternalAccessService {
  private readonly http = inject(HttpClient);

  list(ledgerUuid: string): Observable<ExternalAccessGrant[]> {
    return this.http.get<ExternalAccessGrant[]>(API_ROUTES.ledgers.externalAccesses.root(ledgerUuid));
  }

  create(ledgerUuid: string, payload: CreateExternalAccessRequest): Observable<CreatedExternalAccessGrant> {
    return this.http.post<CreatedExternalAccessGrant>(API_ROUTES.ledgers.externalAccesses.root(ledgerUuid), payload);
  }

  revoke(ledgerUuid: string, grantUuid: string, payload: ExternalAccessCredentials): Observable<void> {
    return this.http.delete<void>(API_ROUTES.ledgers.externalAccesses.byGrantUuid(ledgerUuid, grantUuid), { body: payload });
  }
}
