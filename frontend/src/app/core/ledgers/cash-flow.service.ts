import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import { CashFlowPoint } from './cash-flow.models';

@Injectable({ providedIn: 'root' })
export class CashFlowService {
  private readonly http = inject(HttpClient);

  points(
    ledgerUuid: string,
    currencyUuid: string,
    fromTimestamp: number,
    toTimestamp: number,
    pointWidth: number,
  ): Observable<CashFlowPoint[]> {
    const params = new HttpParams()
      .set('currency_uuid', currencyUuid)
      .set('from_timestamp', fromTimestamp)
      .set('to_timestamp', toTimestamp)
      .set('point_width', pointWidth);
    return this.http.get<CashFlowPoint[]>(`${API_ROUTES.ledgerCashFlow(ledgerUuid)}/points`, { params, withCredentials: true });
  }
}
