import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import { CashFlowPoint, CashFlowSankey } from './cash-flow.models';
import { FinancialEventFilters } from './financial-events.models';

@Injectable({ providedIn: 'root' })
export class CashFlowService {
  private readonly http = inject(HttpClient);

  summary(
    ledgerUuid: string,
    currencyUuid: string,
    filters: Pick<FinancialEventFilters, 'from_timestamp' | 'to_timestamp' | 'account_uuid' | 'category_uuid' | 'event_type' | 'description_search'>,
  ): Observable<CashFlowPoint> {
    let params = new HttpParams()
      .set('currency_uuid', currencyUuid)
      .set('from_timestamp', filters.from_timestamp)
      .set('to_timestamp', filters.to_timestamp);
    if (filters.account_uuid) params = params.set('account_uuid', filters.account_uuid);
    if (filters.category_uuid) params = params.set('category_uuid', filters.category_uuid);
    if (filters.event_type) params = params.set('event_type', filters.event_type);
    if (filters.description_search?.trim()) params = params.set('description_search', filters.description_search.trim());
    return this.http.get<CashFlowPoint>(API_ROUTES.ledgerCashFlow(ledgerUuid), { params });
  }

  points(
    ledgerUuid: string,
    currencyUuid: string,
    fromTimestamp: number,
    toTimestamp: number,
    pointWidth: number,
    filters: Pick<FinancialEventFilters, 'account_uuid' | 'category_uuid' | 'event_type' | 'description_search'> = {},
  ): Observable<CashFlowPoint[]> {
    let params = new HttpParams()
      .set('currency_uuid', currencyUuid)
      .set('from_timestamp', fromTimestamp)
      .set('to_timestamp', toTimestamp)
      .set('point_width', pointWidth);
    if (filters.account_uuid) params = params.set('account_uuid', filters.account_uuid);
    if (filters.category_uuid) params = params.set('category_uuid', filters.category_uuid);
    if (filters.event_type) params = params.set('event_type', filters.event_type);
    if (filters.description_search?.trim()) params = params.set('description_search', filters.description_search.trim());
    return this.http.get<CashFlowPoint[]>(`${API_ROUTES.ledgerCashFlow(ledgerUuid)}/points`, { params });
  }

  sankey(ledgerUuid: string, accountUuid: string, fromTimestamp: number, toTimestamp: number, detailLevel: number): Observable<CashFlowSankey> {
    const params = new HttpParams()
      .set('account_uuid', accountUuid)
      .set('from_timestamp', fromTimestamp)
      .set('to_timestamp', toTimestamp)
      .set('detail_level', detailLevel);
    return this.http.get<CashFlowSankey>(`${API_ROUTES.ledgerCashFlow(ledgerUuid)}/sankey`, { params });
  }

}
