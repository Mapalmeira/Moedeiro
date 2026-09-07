import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';
import { I18nService, TranslationKey } from '../i18n/i18n.service';
import { ApiErrorService } from './api-error';

describe('ApiErrorService', () => {
  let service: ApiErrorService;
  let i18n: I18nService;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('moedeiro-language', 'pt-BR');
    service = TestBed.inject(ApiErrorService);
    i18n = TestBed.inject(I18nService);
  });

  it.each([
    [0, 'errors.serverUnreachable'],
    [429, 'errors.tooManyRequests'],
    [503, 'errors.temporarilyUnavailable'],
  ] as const satisfies readonly (readonly [number, TranslationKey])[])('maps HTTP status %s', (status, key) => {
    const error = new HttpErrorResponse({ status });

    expect(service.message(error)).toBe(i18n.t(key));
  });

  it.each([
    ['Invalid session', 'errors.sessionExpired'],
    ['TOTP required', 'errors.totpRequired'],
    ['TOTP code already used', 'errors.totpAlreadyUsed'],
    ['Invitation not available', 'errors.invitationUnavailable'],
    ['User name not available', 'errors.usernameUnavailable'],
    ['Password update conflict', 'errors.passwordConflict'],
    ['Invalid current password', 'errors.invalidCurrentPassword'],
    ['TOTP already enabled', 'errors.totpAlreadyEnabled'],
    ['TOTP not enabled', 'errors.totpNotEnabled'],
    ['Invalid or expired TOTP setup', 'errors.invalidTotpSetup'],
    ['Ledger not found', 'errors.ledgerNotFound'],
    ['Ledger limit reached', 'errors.ledgerLimitReached'],
    ['Budget limit reached', 'errors.budgetLimitReached'],
    ['Financial event limit reached', 'errors.financialEventLimitReached'],
    ['Account limit reached', 'workspace.limit'],
    ['Currency limit reached', 'workspace.limit'],
    ['Account is in use', 'errors.accountInUse'],
    ['Currency is in use', 'errors.currencyInUse'],
    ['Account name unavailable', 'errors.accountNameUnavailable'],
    ['Currency name unavailable', 'errors.currencyNameUnavailable'],
    ['Account not found', 'errors.accountNotFound'],
    ['Currency not found', 'errors.currencyNotFound'],
    ['Category is in use', 'errors.categoryInUse'],
    ['Category not found', 'errors.categoryNotFound'],
    ['Category name unavailable', 'errors.categoryNameUnavailable'],
    ['Category limit exceeded', 'errors.categoryLimitReached'],
    ['Category depth limit exceeded', 'errors.categoryDepthExceeded'],
    ['Invalid category hierarchy', 'errors.categoryHierarchyInvalid'],
  ] as const satisfies readonly (readonly [string, TranslationKey])[])('maps API detail %s', (detail, key) => {
    const error = new HttpErrorResponse({ status: 409, error: { detail } });

    expect(service.message(error)).toBe(i18n.t(key));
  });

  it('keeps invalid credentials indistinguishable', () => {
    const error = new HttpErrorResponse({ status: 401, error: { detail: 'Invalid credentials' } });

    expect(service.message(error, 'errors.loginFailed')).toBe(i18n.t('errors.loginFailed'));
  });

  it('maps validation errors to their field', () => {
    const error = new HttpErrorResponse({
      status: 422,
      error: { detail: [{ loc: ['body', 'name'] }] },
    });

    expect(service.message(error)).toBe(i18n.t('errors.invalidField', { field: 'name' }));
  });

  it('uses the requested fallback for validation errors without a field', () => {
    const error = new HttpErrorResponse({ status: 422, error: { detail: [{}] } });

    expect(service.message(error, 'errors.ledgerCreateFailed')).toBe(i18n.t('errors.ledgerCreateFailed'));
  });

  it('uses the requested fallback for unknown API details', () => {
    const error = new HttpErrorResponse({ status: 409, error: { detail: 'Unknown detail' } });

    expect(service.message(error, 'errors.currencySaveFailed')).toBe(i18n.t('errors.currencySaveFailed'));
  });

  it('uses the requested fallback for non-HTTP errors', () => {
    expect(service.message(new Error('failed'), 'errors.preferencesSaveFailed')).toBe(
      i18n.t('errors.preferencesSaveFailed'),
    );
  });
});
