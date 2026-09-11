import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import {
  CreateFinancialEventPayload,
  FinancialEvent,
  FinancialEventFilters,
  FinancialEventPage,
  UpdateFinancialEventPayload,
} from './financial-events.models';

@Injectable({ providedIn: 'root' })
export class FinancialEventsService {
  private readonly http = inject(HttpClient);

  list(ledgerUuid: string, filters: FinancialEventFilters): Observable<FinancialEventPage> {
    let params = new HttpParams()
      .set('from_timestamp', filters.from_timestamp)
      .set('to_timestamp', filters.to_timestamp)
      .set('page_size', filters.page_size)
      .set('ascending', filters.ascending ?? false);
    if (filters.account_uuid) params = params.set('account_uuid', filters.account_uuid);
    if (filters.currency_uuid) params = params.set('currency_uuid', filters.currency_uuid);
    if (filters.category_uuid) params = params.set('category_uuid', filters.category_uuid);
    if (filters.event_type) params = params.set('event_type', filters.event_type);
    if (filters.description_search?.trim()) params = params.set('description_search', filters.description_search.trim());
    if (filters.cursor) params = params.set('cursor', filters.cursor);
    return this.http.get<FinancialEventPage>(API_ROUTES.ledgerEvents(ledgerUuid), { params });
  }

  create(ledgerUuid: string, payload: CreateFinancialEventPayload): Observable<FinancialEvent> {
    return this.http.post<FinancialEvent>(API_ROUTES.ledgerEvents(ledgerUuid), payload);
  }

  update(ledgerUuid: string, eventUuid: string, payload: UpdateFinancialEventPayload): Observable<FinancialEvent> {
    return this.http.put<FinancialEvent>(`${API_ROUTES.ledgerEvents(ledgerUuid)}/${encodeURIComponent(eventUuid)}`, payload);
  }

  delete(ledgerUuid: string, eventUuid: string): Observable<void> {
    return this.http.delete<void>(`${API_ROUTES.ledgerEvents(ledgerUuid)}/${encodeURIComponent(eventUuid)}`);
  }
}
