import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import { LedgerCategory, LedgerCategoryPayload, LedgerCategoryTreeNode } from './ledger-categories.models';

@Injectable({ providedIn: 'root' })
export class LedgerCategoriesService {
  private readonly http = inject(HttpClient);

  getTree(ledgerUuid: string): Observable<LedgerCategoryTreeNode[]> {
    return this.http.get<LedgerCategoryTreeNode[]>(`${API_ROUTES.ledgerCategories(ledgerUuid)}/tree`, { withCredentials: true });
  }

  create(ledgerUuid: string, payload: LedgerCategoryPayload): Observable<LedgerCategory> {
    return this.http.post<LedgerCategory>(API_ROUTES.ledgerCategories(ledgerUuid), payload, { withCredentials: true });
  }

  update(ledgerUuid: string, categoryUuid: string, payload: LedgerCategoryPayload): Observable<LedgerCategory> {
    return this.http.put<LedgerCategory>(`${API_ROUTES.ledgerCategories(ledgerUuid)}/${encodeURIComponent(categoryUuid)}`, payload, { withCredentials: true });
  }

  delete(ledgerUuid: string, categoryUuid: string): Observable<void> {
    return this.http.delete<void>(`${API_ROUTES.ledgerCategories(ledgerUuid)}/${encodeURIComponent(categoryUuid)}`, { withCredentials: true });
  }
}
