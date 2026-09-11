import { TestBed } from '@angular/core/testing';
import { HttpRequest, HttpResponse } from '@angular/common/http';
import { of } from 'rxjs';
import { apiCredentialsInterceptor } from './api-credentials.interceptor';

describe('apiCredentialsInterceptor', () => {
  it('adds credentials only to API requests', () => {
    TestBed.runInInjectionContext(() => {
      let apiRequest: HttpRequest<unknown> | undefined;
      apiCredentialsInterceptor(new HttpRequest('GET', '/api/ledgers'), request => { apiRequest = request; return of(new HttpResponse()); }).subscribe();
      expect(apiRequest?.withCredentials).toBe(true);

      let assetRequest: HttpRequest<unknown> | undefined;
      apiCredentialsInterceptor(new HttpRequest('GET', '/assets/icon.svg'), request => { assetRequest = request; return of(new HttpResponse()); }).subscribe();
      expect(assetRequest?.withCredentials).toBe(false);
    });
  });
});
