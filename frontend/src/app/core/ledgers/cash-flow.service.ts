import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import { CashFlowPoint, CashFlowSankey } from './cash-flow.models';

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

  sankey(ledgerUuid: string, accountUuid: string, fromTimestamp: number, toTimestamp: number, detailLevel: number): Observable<CashFlowSankey> {
    const params = new HttpParams()
      .set('account_uuid', accountUuid)
      .set('from_timestamp', fromTimestamp)
      .set('to_timestamp', toTimestamp)
      .set('detail_level', detailLevel);
    return this.http.get<CashFlowSankey>(`${API_ROUTES.ledgerCashFlow(ledgerUuid)}/sankey`, { params, withCredentials: true });
  }

}
